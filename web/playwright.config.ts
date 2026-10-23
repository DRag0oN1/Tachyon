import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: '../tests/e2e',
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  outputDir: './test-results',
  timeout: 30_000,
  use: {
    baseURL: process.env.TACHYON_E2E_BASE_URL ?? 'http://127.0.0.1:5173',
    // Protected CAD and launch fragments must not enter recordings or reports.
    trace: 'off', screenshot: 'off', video: 'off',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'], launchOptions: { args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] } } },
    { name: 'mobile-webkit', use: { ...devices['iPhone 13'] } },
  ],
  webServer: process.env.TACHYON_E2E_BASE_URL ? undefined : {
    command: 'npm run dev', url: 'http://127.0.0.1:5173', reuseExistingServer: !process.env.CI,
  },
});
