import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',

  // Runs once before any test: logs in for each seeded user and writes
  // .auth/tokens.json. Tests consume this file through fixtures/index.ts
  // and stub the refresh endpoint - no per-test login API calls.
  globalSetup: './tests/e2e/setup/global-setup.ts',

  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? 'github' : 'html',

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      testIgnore: /tests\/e2e\/(setup|auth)\//,
    },
    {
      name: 'guest',
      use: { ...devices['Desktop Chrome'] },
      testMatch: /tests\/e2e\/auth\//,
    },
  ],

  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
})
