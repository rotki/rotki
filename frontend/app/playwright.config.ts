import { execSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { defineConfig, devices } from '@playwright/test';

const FRONTEND_PORT = 30301;
const BACKEND_PORT = 30302;
const COLIBRI_PORT = 30303;

const frontendUrl = `http://localhost:${FRONTEND_PORT}`;
const backendUrl = `http://127.0.0.1:${BACKEND_PORT}`;
const colibriUrl = `http://127.0.0.1:${COLIBRI_PORT}`;

const testDir = path.join(process.cwd(), '.e2e');
const dataDir = path.join(testDir, 'data');
const logDir = path.join(testDir, 'logs');

function ensureDirectories(): void {
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
  }
  if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true });
  }
}

ensureDirectories();

/**
 * Detect system Chromium installation for Arch Linux and other systems.
 * Returns the path to chromium if found, undefined otherwise (uses bundled Chromium).
 */
function detectSystemChromium(): string | undefined {
  // Try 'which chromium' first (works on most Linux distros including Arch)
  try {
    const chromiumPath = execSync('which chromium', { encoding: 'utf-8' }).trim();
    if (chromiumPath && fs.existsSync(chromiumPath)) {
      return chromiumPath;
    }
  }
  catch {
    // Command failed, try fallback paths
  }

  // Fallback: common Linux paths
  const fallbackPaths = [
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
    '/snap/bin/chromium',
  ];

  for (const browserPath of fallbackPaths) {
    if (fs.existsSync(browserPath)) {
      return browserPath;
    }
  }

  // No system Chromium found, Playwright will use bundled version
  return undefined;
}

const systemChromium = detectSystemChromium();

// Get the test group from environment (app or balances)
const testGroup = process.env.GROUP;
const testDirPath = testGroup ? `./tests/e2e/specs/${testGroup}` : './tests/e2e/specs';

export default defineConfig({
  testDir: testDirPath,
  timeout: 60_000,
  expect: {
    timeout: 60_000,
  },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  // Backend is single-user, must use 1 worker
  workers: 1,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',
  outputDir: 'tests/e2e/test-results',

  use: {
    baseURL: frontendUrl,
    timezoneId: 'UTC',
    trace: 'retain-on-failure',
    video: process.env.CI ? 'retain-on-failure' : 'off',
    screenshot: 'only-on-failure',
    actionTimeout: 60_000,
    navigationTimeout: 300_000,
  },

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 720 },
        launchOptions: {
          executablePath: systemChromium,
          args: [
            '--disable-gpu',
            '--disable-dev-shm-usage',
            '--disable-extensions',
            '--disable-background-networking',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-component-update',
            '--disable-sync',
          ],
        },
      },
    },
  ],

  webServer: [
    {
      command: `tsx scripts/start-backend.ts --port ${BACKEND_PORT} --data ${dataDir} --logs ${logDir}`,
      url: `${backendUrl}/api/1/ping`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        ROTKEHLCHEN_ENVIRONMENT: 'test',
      },
    },
    {
      command: `tsx scripts/start-colibri.ts --port ${COLIBRI_PORT} --data ${dataDir} --logs ${logDir}`,
      url: `${colibriUrl}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 180_000,
    },
    {
      command: process.env.CI
        ? `vite preview --port ${FRONTEND_PORT}`
        : `tsx scripts/serve.ts --web --port ${FRONTEND_PORT}`,
      url: frontendUrl,
      reuseExistingServer: !process.env.CI,
      timeout: 180_000,
      env: {
        VITE_BACKEND_URL: backendUrl,
        VITE_COLIBRI_URL: colibriUrl,
        // Pass coverage flag to enable source maps in build
        ...(process.env.VITE_COVERAGE && { VITE_COVERAGE: process.env.VITE_COVERAGE }),
      },
    },
  ],
});

export { backendUrl, colibriUrl, dataDir, frontendUrl, logDir };
