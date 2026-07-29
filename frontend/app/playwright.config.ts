import { execSync, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { defineConfig, devices } from '@playwright/test';

const BASE_FRONTEND_PORT = 30301;
const BASE_BACKEND_PORT = 30302;
const BASE_COLIBRI_PORT = 30303;
const BASE_MOCK_RPC_PORT = 30304;

const BASE_PORTS = [BASE_FRONTEND_PORT, BASE_BACKEND_PORT, BASE_COLIBRI_PORT, BASE_MOCK_RPC_PORT];
const PORT_BLOCK_STRIDE = 10;
const MAX_PORT_BLOCKS = 10;

/**
 * Synchronously check whether a port can be bound. Playwright config files are loaded
 * synchronously, so this shells out to a short-lived node instead of using an async
 * `net.createServer` probe.
 */
function isPortFree(port: number): boolean {
  const probe = 'const net = require("node:net");'
    + 'const server = net.createServer();'
    + 'server.once("error", () => process.exit(1));'
    + 'server.once("listening", () => server.close(() => process.exit(0)));'
    + `server.listen(${port}, "127.0.0.1");`;
  return spawnSync(process.execPath, ['-e', probe], { stdio: 'ignore' }).status === 0;
}

/**
 * The four services use fixed ports, so a second checkout running e2e at the same time
 * would collide (or worse, silently reuse the other checkout's servers via
 * `reuseExistingServer`). Move the whole block up in steps of 10 until every port in it
 * is free. CI is pinned to the base block: the build job bakes the backend/colibri URLs
 * into the frontend bundle from its own env, so the ports cannot be chosen here.
 */
function resolvePortOffset(): number {
  if (process.env.CI)
    return 0;

  for (let block = 0; block < MAX_PORT_BLOCKS; block++) {
    const offset = block * PORT_BLOCK_STRIDE;
    if (BASE_PORTS.every(port => isPortFree(port + offset))) {
      if (offset > 0)
        console.log(`[e2e] ports ${BASE_FRONTEND_PORT}-${BASE_MOCK_RPC_PORT} are busy, using +${offset}`);

      return offset;
    }
  }

  throw new Error(
    `Could not find a free block of e2e ports after ${MAX_PORT_BLOCKS} attempts starting at ${BASE_FRONTEND_PORT}`,
  );
}

const portOffset = resolvePortOffset();

const FRONTEND_PORT = BASE_FRONTEND_PORT + portOffset;
const BACKEND_PORT = BASE_BACKEND_PORT + portOffset;
const COLIBRI_PORT = BASE_COLIBRI_PORT + portOffset;
const MOCK_RPC_PORT = BASE_MOCK_RPC_PORT + portOffset;

const frontendUrl = `http://localhost:${FRONTEND_PORT}`;
const backendUrl = `http://127.0.0.1:${BACKEND_PORT}`;
const colibriUrl = `http://127.0.0.1:${COLIBRI_PORT}`;
const mockRpcUrl = `http://127.0.0.1:${MOCK_RPC_PORT}`;

// `.e2e` is resolved from the cwd, so parallel runs in different worktrees already get
// their own data and log directories.
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

/**
 * Interactive runs (`--ui`, `--headed`, `--debug`) keep the Vite dev server so HMR and
 * un-minified sources are available while poking at a failing spec. Every other local
 * run builds once and serves the output with `vite preview`: the dev server holds the
 * whole module graph plus its transform cache in memory (multiple GB on this codebase),
 * while preview only serves static files. CI already builds in a separate workflow step,
 * so there the command is a bare `vite preview`.
 */
function isInteractiveRun(): boolean {
  if (process.env.PWDEBUG)
    return true;

  return process.argv.some(arg => arg === '--headed' || arg === '--debug' || arg === '--ui' || arg.startsWith('--ui-'));
}

const interactive = isInteractiveRun();

function buildFrontendCommand(): string {
  // --no-open: this is a test harness, don't pop a browser tab (serve.ts
  // auto-opens in web mode by default). Playwright drives its own browser.
  if (interactive)
    return `tsx scripts/serve.ts --web --no-open --port ${FRONTEND_PORT}`;

  // --strictPort: fail loudly instead of silently serving on another port, which would
  // leave the tests pointing at a URL nothing is listening on.
  const preview = `vite preview --port ${FRONTEND_PORT} --strictPort`;
  // CI builds the frontend in its own workflow job and downloads the artifact.
  return process.env.CI ? preview : `pnpm run build:app --mode e2e && ${preview}`;
}

const frontendCommand = buildFrontendCommand();

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
      command: `tsx tests/e2e/rpc-mock/server.ts`,
      url: `${mockRpcUrl}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 10_000,
      env: {
        MOCK_RPC_PORT: String(MOCK_RPC_PORT),
        MOCK_RPC_MODE: process.env.MOCK_RPC_MODE ?? 'replay',
        ...(process.env.MOCK_RPC_TARGET && { MOCK_RPC_TARGET: process.env.MOCK_RPC_TARGET }),
      },
    },
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
      command: frontendCommand,
      url: frontendUrl,
      reuseExistingServer: !process.env.CI,
      // The local non-interactive path builds before serving (~15s on a warm machine),
      // so it gets more headroom than starting a dev server or serving an existing dist.
      timeout: interactive || process.env.CI ? 180_000 : 300_000,
      env: {
        VITE_BACKEND_URL: backendUrl,
        VITE_COLIBRI_URL: colibriUrl,
        // Pass coverage flag to enable source maps in build
        ...(process.env.VITE_COVERAGE && { VITE_COVERAGE: process.env.VITE_COVERAGE }),
      },
    },
  ],
});

export { backendUrl, colibriUrl, dataDir, frontendUrl, logDir, mockRpcUrl };
