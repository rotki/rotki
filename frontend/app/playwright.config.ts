import { execSync, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { defineConfig, devices } from '@playwright/test';

const BASE_FRONTEND_PORT = 30301;
const BASE_BACKEND_PORT = 30302;
const BASE_COLIBRI_PORT = 30303;
const BASE_MOCK_RPC_PORT = 30304;
// starling's reverse proxy: the single origin the tests address. Core and colibri
// stay on their own ports as its upstreams, but nothing dials them directly.
const BASE_PROXY_PORT = 30305;
// starling also wants an MCP port. Nothing in the suite uses it, but it must not
// collide with another block, so it rides along.
const BASE_MCP_PORT = 30306;

const BASE_PORTS = [
  BASE_FRONTEND_PORT,
  BASE_BACKEND_PORT,
  BASE_COLIBRI_PORT,
  BASE_MOCK_RPC_PORT,
  BASE_PROXY_PORT,
  BASE_MCP_PORT,
];
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
 * The services use fixed ports, so a second checkout running e2e at the same time
 * would collide (or worse, silently reuse the other checkout's servers via
 * `reuseExistingServer`). Move the whole block up in steps of 10 until every port in it
 * is free. CI is pinned to the base block: the build job bakes the backend/colibri URLs
 * into the frontend bundle from its own env, so the ports cannot be chosen here.
 *
 * The offset must be resolved exactly once per run. Playwright loads this config in the
 * main process and again in every worker, and by the time a worker loads it the servers
 * the main process started are occupying the block it picked. A second probe would see
 * them as busy and shift, leaving the helpers that import `backendUrl` pointing at a port
 * nothing is listening on. Publishing the result to the env makes the workers - which are
 * children of the main process - inherit the decision instead of re-deciding.
 */
function resolvePortOffset(): number {
  if (process.env.CI)
    return 0;

  // A non-empty value is either inherited from the main process or set deliberately in the
  // shell to pin a block; `'0'` is truthy, so the base block still round-trips.
  const inherited = process.env.E2E_PORT_OFFSET;
  if (inherited && Number.isInteger(Number(inherited)))
    return Number(inherited);

  for (let block = 0; block < MAX_PORT_BLOCKS; block++) {
    const offset = block * PORT_BLOCK_STRIDE;
    if (BASE_PORTS.every(port => isPortFree(port + offset))) {
      if (offset > 0)
        console.log(`[e2e] ports ${BASE_FRONTEND_PORT}-${BASE_MOCK_RPC_PORT} are busy, using +${offset}`);

      process.env.E2E_PORT_OFFSET = String(offset);
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
const PROXY_PORT = BASE_PROXY_PORT + portOffset;
const MCP_PORT = BASE_MCP_PORT + portOffset;

const frontendUrl = `http://localhost:${FRONTEND_PORT}`;
// One origin for both backends, matching every shipping mode: `/api/1/*` and
// `/ws/` reach core, `/colibri/*` reaches colibri with the prefix stripped.
const backendUrl = `http://127.0.0.1:${PROXY_PORT}`;
const colibriUrl = `${backendUrl}/colibri`;
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

/**
 * CI runs against the browser the runner image already ships. runner-images symlinks its
 * Chromium to /usr/bin/chromium, so detectSystemChromium() finds it and no `playwright
 * install` step is needed. That binary tracks the runner image rather than the Playwright
 * release, so the browser version is deliberately not pinned. If a future image drops the
 * symlink, fail here with a named error instead of silently falling back to a bundled
 * browser that CI never downloads.
 */
function resolveChromium(): string | undefined {
  const detected = detectSystemChromium();
  if (!detected && process.env.CI) {
    throw new Error(
      'No system Chromium found. CI runs against the runner-provided browser at '
      + '/usr/bin/chromium and does not run `playwright install`.',
    );
  }
  return detected;
}

const systemChromium = resolveChromium();

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
      // One supervisor brings up core and colibri and fronts both behind its
      // proxy. The gate is the supervisor's own `/health`, which answers 200 only
      // once every service has passed its readiness probe (core `/api/1/ping`,
      // colibri `/health`). Probing core through the proxy instead let the suite
      // start with colibri still coming up: the proxy binds and serves before the
      // tree is brought up, so core answering says nothing about the rest.
      command: `tsx scripts/start-starling.ts --port ${PROXY_PORT} --core-port ${BACKEND_PORT} --colibri-port ${COLIBRI_PORT} --mcp-port ${MCP_PORT} --data ${dataDir} --logs ${logDir}`,
      url: `${backendUrl}/health`,
      reuseExistingServer: !process.env.CI,
      // Covers a cold `cargo run` for both Rust services on a fresh checkout.
      timeout: 180_000,
      // Playwright otherwise SIGKILLs the server's process tree. starling puts
      // core and colibri in their own process groups so it can tree-kill them
      // itself, so that kill never reaches them and both survive the run. Send
      // SIGTERM instead and wait, which lets the wrapper drive the ordered
      // shutdown; the window covers starling's own 10s grace with room to spare.
      gracefulShutdown: { signal: 'SIGTERM', timeout: 20_000 },
      env: {
        ROTKEHLCHEN_ENVIRONMENT: 'test',
      },
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
        // Pass coverage flag to enable source maps in build
        ...(process.env.VITE_COVERAGE && { VITE_COVERAGE: process.env.VITE_COVERAGE }),
      },
    },
  ],
});

export { backendUrl, colibriUrl, dataDir, frontendUrl, logDir, mockRpcUrl };
