import { spawn } from 'node:child_process';
import fs from 'node:fs';
import { platform } from 'node:os';
import path from 'node:path';
import process from 'node:process';
import consola from 'consola';
import { DEFAULT_PORTS, type InstanceRuntime } from '../dev-instance';
import { formatPort } from '../dev-instance/format';
import { getDebuggerPort, isUsingUvForPython, selectPort } from './prerequisites';
import { startProcess } from './process-pool';

const logger = consola.withTag('dev:services');

const colors = {
  red: (msg: string) => `\u001B[31m${msg}\u001B[0m`,
  green: (msg: string) => `\u001B[32m${msg}\u001B[0m`,
  yellow: (msg: string) => `\u001B[33m${msg}\u001B[0m`,
  magenta: (msg: string) => `\u001B[35m${msg}\u001B[0m`,
} as const;

const PROXY = 'proxy';
const ROTKI = 'rotki';
const BACKEND = 'backend';
const COLIBRI = 'colibri';

const READINESS_TIMEOUT_MS = 60_000;
const READINESS_POLL_MS = 250;

const isWindows = platform() === 'win32';

/**
 * Mirrors `__get_windows_cargo_env` in `package.py`: when colibri builds on
 * Windows, `rusqlite`'s `bundled-sqlcipher-vendored-openssl` feature compiles
 * OpenSSL from source, whose Configure script is a Perl script. Git for
 * Windows ships a mingw64 Perl that mishandles string interpolation in OpenSSL's
 * Configure (e.g. eats `$M` from `SYS$MANAGER:[OPENSSL]`), making the build
 * fail with a cryptic `Number found where operator expected` error. Strawberry
 * Perl handles this correctly, so we prepend it on PATH.
 *
 * Important: Windows env is case-insensitive, but Node spawns children with
 * the literal keys you pass. If we add `PATH` while `process.env` still has
 * `Path`, the child receives both and which one wins is undefined — the
 * original Git Perl keeps winning. We must replace the existing key in place
 * (not add a duplicate-cased one).
 *
 * Returns undefined on POSIX, or null on Windows when Strawberry isn't
 * installed (caller decides whether to warn/abort).
 */
function buildColibriEnv(): Record<string, string> | null | undefined {
  if (!isWindows)
    return undefined;
  const strawberryPaths = [
    'C:\\Strawberry\\perl\\bin',
    'C:\\Strawberry\\perl\\site\\bin',
    'C:\\Strawberry\\c\\bin',
  ];
  const existing = strawberryPaths.filter(p => fs.existsSync(p));
  if (existing.length === 0)
    return null;

  const merged: Record<string, string> = {};
  let pathKey = 'Path';
  for (const [key, value] of Object.entries(process.env)) {
    if (value === undefined)
      continue;
    if (key.toUpperCase() === 'PATH') {
      pathKey = key;
      continue;
    }
    merged[key] = value;
  }
  const currentPath = process.env.Path ?? process.env.PATH ?? '';
  const parts = currentPath.split(';').filter(p => p && !existing.includes(p));
  merged[pathKey] = [...existing, ...parts].join(';');
  return merged;
}

export interface BackendEnv {
  VITE_BACKEND_URL: string;
  VITE_COLIBRI_URL: string;
}

export interface BackendSpawnOptions {
  webPort: number;
  strictPort: boolean;
  logDir: string;
  dataDir?: string;
  profilingArgs?: string;
  profilingCmd?: string;
}

async function startPythonBackend(opts: BackendSpawnOptions): Promise<number> {
  const chosenPort = opts.strictPort ? opts.webPort : await selectPort(opts.webPort);
  logger.info(`Starting python backend on port ${formatPort(chosenPort)}`);

  const args = [
    ...(opts.profilingArgs ? opts.profilingArgs.split(' ') : []),
    ...(opts.profilingCmd ? ['python'] : []),
    '-m',
    'rotkehlchen',
    '--rest-api-port',
    chosenPort.toString(),
    '--api-cors',
    'http://localhost:*',
    '--logfile',
    `${path.join(opts.logDir, 'backend.log')}`,
    ...(opts.dataDir ? ['--data-dir', opts.dataDir] : []),
  ];

  // `uv run --locked` honours uv.lock and errors if it's out of date,
  // matching `cargo run --locked` semantics — no silent dep drift in dev.
  const defaultPythonCmd = isUsingUvForPython() ? 'uv run --locked python' : 'python';
  startProcess(opts.profilingCmd ?? defaultPythonCmd, colors.yellow(BACKEND), BACKEND, args, {
    cwd: path.join('..'),
  });
  return chosenPort;
}

interface ColibriSpawnOptions {
  colibriPort: number;
  strictPort: boolean;
  logDir: string;
  dataDir?: string;
}

async function buildColibriEagerly(cwd: string): Promise<void> {
  // Windows-only: `rusqlite`'s `bundled-sqlcipher-vendored-openssl` feature
  // compiles OpenSSL from source, which on a cold cache can take several
  // minutes on Windows — well past the readiness timeout. Run `cargo build`
  // synchronously first so the user sees the compile progress, and the
  // subsequent `cargo run` only races the socket bind. Incremental rebuilds
  // are near-instant, so this is cheap once the cache is warm.
  logger.info('Pre-building colibri (cargo build --locked) — first build compiles vendored openssl and may take a while');
  const buildEnv = buildColibriEnv();
  if (buildEnv === null) {
    logger.warn(
      'Strawberry Perl not found at C:\\Strawberry — OpenSSL build will likely fail. '
      + 'Install Strawberry Perl from https://strawberryperl.com and re-run.',
    );
  }
  else if (buildEnv) {
    logger.info('Prioritizing Strawberry Perl on PATH for cargo build (vendored openssl)');
  }
  await new Promise<void>((resolve, reject) => {
    const child = spawn('cargo', ['build', '--locked'], {
      cwd,
      stdio: 'inherit',
      shell: true,
      windowsHide: true,
      env: buildEnv ?? process.env,
    });
    child.on('exit', (code) => {
      if (code === 0)
        resolve();
      else
        reject(new Error(`cargo build --locked exited with code ${code}`));
    });
    child.on('error', reject);
  });
}

async function startColibriService(opts: ColibriSpawnOptions): Promise<number> {
  const chosenPort = opts.strictPort ? opts.colibriPort : await selectPort(opts.colibriPort);

  const colibriCwd = path.join('..', 'colibri');
  if (isWindows)
    await buildColibriEagerly(colibriCwd);

  logger.info(`Starting colibri on port ${formatPort(chosenPort)}`);

  // `cargo run --locked` rebuilds incrementally on its own; on win32 we
  // already pre-built above, so this is just a launch.
  const colibriArgs: string[] = [
    `--logfile-path=${path.join(opts.logDir, 'colibri.log')}`,
    `--port=${chosenPort}`,
    '--api-cors=http://localhost:*',
    ...(opts.dataDir ? [`--data-directory=${opts.dataDir}`] : []),
  ];

  startProcess('cargo run --locked -- ', colors.red(COLIBRI), COLIBRI, colibriArgs, {
    cwd: colibriCwd,
    env: buildColibriEnv(),
  });
  return chosenPort;
}

export interface BackendServicesOptions {
  webPort: number;
  colibriPort: number;
  strictPort: boolean;
  dataDir?: string;
  profilingArgs?: string;
  profilingCmd?: string;
}

export async function startBackendServices(opts: BackendServicesOptions): Promise<BackendEnv> {
  const logDir = path.join(process.cwd(), 'logs');
  if (!fs.existsSync(logDir))
    fs.mkdirSync(logDir);

  // python and colibri are independent — start them concurrently so the slower
  // one (cargo build on first run) overlaps with python's startup.
  const [restApiPort, colibriHttpPort] = await Promise.all([
    startPythonBackend({
      webPort: opts.webPort,
      strictPort: opts.strictPort,
      logDir,
      dataDir: opts.dataDir,
      profilingArgs: opts.profilingArgs,
      profilingCmd: opts.profilingCmd,
    }),
    startColibriService({
      colibriPort: opts.colibriPort,
      strictPort: opts.strictPort,
      logDir,
      dataDir: opts.dataDir,
    }),
  ]);

  return {
    VITE_BACKEND_URL: `http://localhost:${restApiPort}`,
    VITE_COLIBRI_URL: `http://localhost:${colibriHttpPort}`,
  };
}

async function waitForHttpReady(
  label: string,
  port: number,
  pathname: string,
  timeoutMs: number = READINESS_TIMEOUT_MS,
): Promise<boolean> {
  const deadline = Date.now() + timeoutMs;
  const url = `http://127.0.0.1:${port}${pathname}`;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(url, { signal: AbortSignal.timeout(2_000) });
      if (res.ok) {
        logger.info(`${label} ready on port ${formatPort(port)}`);
        return true;
      }
    }
    catch {
      // not yet listening / not yet responding — keep polling
    }
    await new Promise(resolve => setTimeout(resolve, READINESS_POLL_MS));
  }
  logger.error(`${label} on port ${formatPort(port)} did not respond to ${pathname} within ${timeoutMs}ms`);
  return false;
}

export async function waitForBackendReady(port: number, timeoutMs: number = READINESS_TIMEOUT_MS): Promise<boolean> {
  return waitForHttpReady('backend', port, '/api/1/ping', timeoutMs);
}

export async function waitForColibriReady(port: number, timeoutMs: number = READINESS_TIMEOUT_MS): Promise<boolean> {
  return waitForHttpReady('colibri', port, '/health', timeoutMs);
}

export interface DevServerOptions {
  noElectron: boolean;
  devPort?: number;
  backendEnv?: BackendEnv;
  onExit?: () => void;
}

export function startDevServer(opts: DevServerOptions): void {
  logger.info('Starting rotki dev mode');

  // --remote-debugging-port only does something in electron mode (it forwards
  // to the spawned electron child via setupMainPackageWatcher). In --web mode
  // serve.ts ignores it, so don't bother passing it.
  const debuggerPort = opts.noElectron ? null : getDebuggerPort();
  const debuggerArgs = debuggerPort ? ` --remote-debugging-port=${debuggerPort}` : '';
  if (debuggerArgs)
    logger.info(`starting rotki with args:${debuggerArgs}`);

  const baseServeCmd = opts.noElectron ? 'pnpm run --filter rotki serve' : 'pnpm run --filter rotki electron:serve';
  // Forward `--port` to the serve script directly — no `--` separator. With
  // `--` cac inside serve.ts treats following flags as positional and ignores
  // `--port`, so the dev server keeps listening on its default 8080.
  const serveCmd = opts.noElectron && opts.devPort !== undefined
    ? `${baseServeCmd} --port ${opts.devPort}`
    : baseServeCmd;

  const child = startProcess(`${serveCmd}${debuggerArgs}`, colors.magenta(ROTKI), ROTKI, [], {
    env: opts.backendEnv ? { ...opts.backendEnv } : undefined,
  });

  child.on('exit', () => {
    logger.info('dev rotki process exited');
    opts.onExit?.();
  });
}

export function startDevProxy(env?: Record<string, string>): void {
  const portInfo = env?.PORT ? ` on port ${formatPort(env.PORT)}` : '';
  logger.info(`Starting dev-proxy${portInfo}`);
  startProcess('pnpm run --filter @rotki/dev-proxy serve', colors.green(PROXY), PROXY, [], { env });
}

export interface DevEnvironmentOptions {
  webPort: number;
  colibriPort: number;
  noElectron: boolean;
  profilingArgs?: string;
  profilingCmd?: string;
  instance: InstanceRuntime | null;
  /** Whether to spawn the dev-proxy in front of the backend. */
  useProxy: boolean;
  onChildExit: () => void;
}

async function awaitBackendsReady(restApiPort: number | null, colibriPort: number | null): Promise<void> {
  // Block the dev server on both services being live so Vite doesn't proxy
  // requests to a backend that hasn't bound its socket yet (manifests as a
  // burst of ECONNREFUSED on first load). Probes run concurrently — colibri
  // is usually slower on a cold cargo build than python's import startup.
  // If either probe times out we abort: the previous "warn and continue"
  // behaviour produced a dev server pointed at a non-existent backend.
  const [backendOk, colibriOk] = await Promise.all([
    restApiPort !== null ? waitForBackendReady(restApiPort) : Promise.resolve(true),
    colibriPort !== null ? waitForColibriReady(colibriPort) : Promise.resolve(true),
  ]);
  if (backendOk && colibriOk)
    return;
  const failed = [!backendOk && 'backend', !colibriOk && 'colibri'].filter(Boolean).join(' and ');
  throw new Error(`${failed} did not become ready — refusing to start the dev server.`);
}

async function startBackendForMode(
  instance: InstanceRuntime | null,
  opts: DevEnvironmentOptions,
): Promise<{ backendEnv: BackendEnv; devPort: number | undefined }> {
  const backendEnv = await startBackendServices({
    webPort: instance ? instance.ports.restApi : opts.webPort,
    colibriPort: instance ? instance.ports.colibri : opts.colibriPort,
    strictPort: instance !== null,
    dataDir: instance?.dir,
    profilingArgs: opts.profilingArgs,
    profilingCmd: opts.profilingCmd,
  });

  const restApiPort = instance?.ports.restApi ?? extractPort(backendEnv.VITE_BACKEND_URL);
  const colibriPort = instance?.ports.colibri ?? extractPort(backendEnv.VITE_COLIBRI_URL);
  await awaitBackendsReady(restApiPort, colibriPort);
  return { backendEnv, devPort: instance?.ports.dev };
}

function spawnProxyForBackend(instance: InstanceRuntime | null, backendEnv: BackendEnv): void {
  // Web mode — we know the actual backend port (instance slot or selectPort
  // drift). Point VITE_BACKEND_URL at the proxy so Vite picks it up.
  const proxyPort = instance?.ports.proxy ?? DEFAULT_PORTS.proxy;
  process.env.VITE_BACKEND_URL = `http://127.0.0.1:${proxyPort}`;
  startDevProxy({ PORT: String(proxyPort), BACKEND: backendEnv.VITE_BACKEND_URL });
}

function spawnProxyForElectron(): void {
  // Electron mode — electron's main process spawns its own backend; start-dev
  // doesn't know the chosen port. Match the long-standing convention:
  // backend defaults to DEFAULT_PORTS.restApi, proxy listens on DEFAULT_PORTS.proxy
  // and forwards. Set VITE_BACKEND_URL so the Vite-served renderer hits the proxy.
  process.env.VITE_BACKEND_URL = `http://127.0.0.1:${DEFAULT_PORTS.proxy}`;
  startDevProxy({
    PORT: String(DEFAULT_PORTS.proxy),
    BACKEND: `http://127.0.0.1:${DEFAULT_PORTS.restApi}`,
  });
}

function pointFrontendAtBackend(backendEnv: BackendEnv): void {
  // No proxy — Vite reads VITE_BACKEND_URL and connects directly. The Python
  // backend's --api-cors=http://localhost:* permits the Vite origin.
  process.env.VITE_BACKEND_URL = backendEnv.VITE_BACKEND_URL;
}

export async function startDevelopmentEnvironment(opts: DevEnvironmentOptions): Promise<void> {
  const { instance, noElectron, useProxy, onChildExit } = opts;

  let backendEnv: BackendEnv | undefined;
  let devPort: number | undefined;

  if (noElectron) {
    ({ backendEnv, devPort } = await startBackendForMode(instance, opts));
  }

  if (backendEnv) {
    if (useProxy)
      spawnProxyForBackend(instance, backendEnv);
    else
      pointFrontendAtBackend(backendEnv);
  }
  else if (useProxy) {
    // Electron mode + proxy: spawn it with defaults (electron's backend lands
    // at 4242, proxy fronts it at 4243). This matches the pre-refactor
    // behaviour triggered by VITE_BACKEND_URL being present in .env.
    spawnProxyForElectron();
  }

  startDevServer({ noElectron, devPort, backendEnv, onExit: onChildExit });

  // win32 historically had no readiness wait — give hot-reload subscribers a
  // moment to attach before the first Vite compile.
  if (noElectron && platform() === 'win32') {
    await new Promise(resolve => setTimeout(resolve, 1_000));
  }
}

function extractPort(url: string): number | null {
  try {
    return Number.parseInt(new URL(url).port, 10) || null;
  }
  catch {
    return null;
  }
}
