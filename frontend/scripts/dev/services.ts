import { spawn } from 'node:child_process';
import fs from 'node:fs';
import { platform } from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { buildCargoEnv, STRAWBERRY_MISSING_WARNING } from '../../app/shared/cargo-env';
import { isPortFree } from '../../app/shared/port-utils';
import { DEFAULT_PORTS, type InstanceRuntime } from '../dev-instance';
import { formatPort } from '../dev-instance/format';
import { createDevLogger } from './logger';
import { getDebuggerPort, isUsingUvForPython } from './prerequisites';
import { startProcess } from './process-pool';
import { type StarlingDevEnv, startStarlingSupervisor } from './starling';

const logger = createDevLogger('dev:services');

const colors = {
  green: (msg: string) => `\u001B[32m${msg}\u001B[0m`,
  magenta: (msg: string) => `\u001B[35m${msg}\u001B[0m`,
} as const;

const PROXY = 'proxy';
const APP = 'app';

/**
 * Warm the rust builds a dev launch needs before either mode reaches its start
 * point, so a fresh worktree doesn't hit a cold compile at launch. Both modes
 * need both packages: starling supervises core and colibri in web mode exactly
 * as it does under electron. They share one Cargo invocation and target
 * directory, allowing their common dependencies to compile only once.
 *
 * The python deps are synced afterwards rather than concurrently: both stages
 * inherit stdio, and serializing keeps `uv sync`'s resolver output from being
 * interleaved into the middle of cargo's progress bars.
 */
export async function warmDevServices(): Promise<void> {
  await buildRustServices();
  await syncPythonDeps();
}

/**
 * Sync the backend deps from `uv.lock` before anything tries to launch python.
 * `--locked` errors instead of silently re-resolving when the lock is stale,
 * matching the `uv run --locked` the backend is actually started with - without
 * this, a fresh worktree (or a rebase that moved `uv.lock`) pays the resolve at
 * spawn time and can blow the readiness timeout.
 *
 * Only the uv path is synced. With a venv active, the deps are the developer's to
 * manage and `verifyBackendReady()` already checks the venv actually answers.
 */
async function syncPythonDeps(): Promise<void> {
  if (!isUsingUvForPython())
    return;
  logger.info('Syncing python deps (uv sync --locked)');
  await runCommand('uv', ['sync', '--locked'], path.join('..'));
}

async function buildRustServices(): Promise<void> {
  const packages = ['-p', 'colibri', '-p', 'starling'];
  logger.info(`Warming Rust services (cargo build --locked ${packages.join(' ')}) so the dev launch does not compile at startup; the first build may take a while`);
  const buildEnv = buildCargoEnv();
  if (buildEnv === null) {
    logger.warn(STRAWBERRY_MISSING_WARNING);
  }
  else if (buildEnv) {
    logger.info('Prioritizing Strawberry Perl on PATH for cargo build (vendored openssl)');
  }
  await runCargoBuild(path.join('..'), ['build', '--locked', ...packages], buildEnv ?? undefined);
}

/** `cargo` with the Colibri-compatible PATH shim applied by the caller. */
async function runCargoBuild(cwd: string, args: string[], env?: Record<string, string>): Promise<void> {
  await runCommand('cargo', args, cwd, env);
}

/**
 * Run a warm-up command to completion, inheriting stdio so its progress is
 * visible. `env` undefined inherits `process.env`; pass an explicit map (e.g.
 * colibri's Strawberry-Perl PATH shim) to override it.
 */
async function runCommand(cmd: string, args: string[], cwd: string, env?: Record<string, string>): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    const child = spawn(cmd, args, {
      cwd,
      stdio: 'inherit',
      shell: true,
      windowsHide: true,
      env: env ?? process.env,
    });
    child.on('exit', (code) => {
      if (code === 0)
        resolve();
      else
        reject(new Error(`${cmd} ${args.join(' ')} exited with code ${code}`));
    });
    child.on('error', reject);
  });
}

export interface DevServerOptions {
  noElectron: boolean;
  devPort?: number;
  backendEnv?: StarlingDevEnv;
  /** Extra env forwarded to the serve child (electron instance ports/data dir). */
  extraEnv?: Record<string, string>;
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
  // `--port`, so the dev server keeps listening on its default 8080. Applies to
  // both modes: in electron mode this runs the instance's Vite dev server on the
  // instance `dev` port (serve.ts sets VITE_DEV_SERVER_URL from it, so electron
  // loads the right origin); plain `pnpm dev` leaves devPort undefined → 8080.
  const serveCmd = opts.devPort !== undefined
    ? `${baseServeCmd} --port ${opts.devPort}`
    : baseServeCmd;

  const env = { ...opts.backendEnv, ...opts.extraEnv };
  const child = startProcess(`${serveCmd}${debuggerArgs}`, colors.magenta(APP), APP, [], {
    env: Object.keys(env).length > 0 ? env : undefined,
    // Electron mode only: this chain ends in an electron window, the one child
    // that can act on a polite close and quit cleanly (which is what lets starling
    // stop the backends gracefully). In web mode it ends in vite, which cannot.
    windowed: !opts.noElectron,
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
  /** Port core starts probing from in web mode (`--web-port`). */
  webPort: number;
  /** Port colibri starts probing from in web mode. */
  colibriPort: number;
  noElectron: boolean;
  instance: InstanceRuntime | null;
  /** Whether to spawn the dev-proxy in front of the backend. */
  useProxy: boolean;
  onChildExit: () => void;
}

/**
 * Bring the backend tree up for web mode. starling supervises core and colibri
 * and fronts both behind its own proxy, so there is no readiness polling here:
 * the `start` control request it is driven with resolves only once the whole
 * tree is up. In instance mode every port starling binds — core, colibri, its
 * own proxy and mcp — comes from the reserved slot, so the slot owns them all.
 */
async function startBackendForMode(
  instance: InstanceRuntime | null,
  opts: DevEnvironmentOptions,
): Promise<{ backendEnv: StarlingDevEnv; corePort: number; devPort: number | undefined }> {
  const logDir = path.join(process.cwd(), 'logs');
  if (!fs.existsSync(logDir))
    fs.mkdirSync(logDir);

  if (opts.useProxy)
    await assertDevProxyPortFree(devProxyPort(instance));

  const { env, ports } = await startStarlingSupervisor({
    logDir,
    dataDir: instance?.dir,
    corePort: instance ? instance.ports.restApi : opts.webPort,
    colibriPort: instance ? instance.ports.colibri : opts.colibriPort,
    proxyPort: instance ? instance.ports.starlingProxy : DEFAULT_PORTS.starlingProxy,
    mcpPort: instance ? instance.ports.mcp : DEFAULT_PORTS.mcp,
    // With the dev-proxy on, starling forwards `/api/1/*` through it. The port is
    // known up front (a slot reservation or the default), so it can be named at
    // launch even though the proxy itself starts once starling is up.
    coreUpstreamPort: opts.useProxy ? devProxyPort(instance) : undefined,
    // An instance owns its slot outright; otherwise the defaults are only a
    // starting point and a busy port walks up, as it did before starling.
    strictPorts: instance !== null,
  });
  return { backendEnv: env, corePort: ports.corePort, devPort: instance?.ports.dev };
}

function devProxyPort(instance: InstanceRuntime | null): number {
  return instance?.ports.proxy ?? DEFAULT_PORTS.proxy;
}

/**
 * starling is told the dev-proxy's port at launch, before the proxy has bound it,
 * and unlike starling's own ports it never walks upward. A leftover proxy from an
 * earlier run still holding the port would take the new one's place silently —
 * still pointed at that run's core — so every `/api/1/*` call would reach the
 * wrong backend with nothing reporting it. Refuse instead.
 */
async function assertDevProxyPortFree(port: number): Promise<void> {
  if (await isPortFree(port, '127.0.0.1'))
    return;

  throw new Error(
    `The dev-proxy port ${formatPort(String(port))} is already in use, most likely by a dev-proxy `
    + 'from an earlier run. starling would forward every /api/1/* request to it instead of to this '
    + 'run\'s backend. Stop it, or start without the proxy (--no-proxy).',
  );
}

function spawnProxyForBackend(instance: InstanceRuntime | null, corePort: number): void {
  // The premium dev-proxy sits *between* starling and core:
  // frontend -> starling proxy -> dev-proxy -> core. starling stays the single
  // renderer origin in every mode, so `VITE_BACKEND_URL` is untouched here — it
  // used to be redirected at the proxy, which the vite child then overrode with
  // starling's url anyway, leaving the proxy running with nothing routed to it.
  //
  // Only `/api/1/*` is routed through it, which is the whole of what it
  // intercepts. `/colibri/*`, `/ws/*` and `/_control` never leave starling.
  startDevProxy({
    PORT: String(devProxyPort(instance)),
    BACKEND: `http://127.0.0.1:${corePort}`,
  });
}

function spawnProxyForElectron(instance: InstanceRuntime | null): void {
  // Electron spawns its own starling, which routes `/api/1/*` through this proxy
  // once it is told the port (ROTKI_DEV_CORE_UPSTREAM_PORT, below). The renderer
  // is handed starling's origin over IPC and must keep it, so nothing here
  // touches VITE_BACKEND_URL: redirecting it would only be overridden by that
  // IPC value anyway, which is how the proxy came to be bypassed entirely.
  //
  // The backend port is the one electron is told to bind, or the default.
  const backendPort = instance?.ports.restApi ?? DEFAULT_PORTS.restApi;
  startDevProxy({
    PORT: String(devProxyPort(instance)),
    BACKEND: `http://127.0.0.1:${backendPort}`,
  });
}

/**
 * Env handed to the electron child in instance mode. Electron spawns its own
 * backend + colibri, so it needs the instance's reserved ports and data dir to
 * bind there instead of the shared defaults. Returns undefined outside instance
 * mode, leaving electron on its default ports / configured data dir.
 */
function instanceEnvForElectron(instance: InstanceRuntime | null): Record<string, string> {
  if (!instance)
    return {};
  return {
    ROTKI_INSTANCE_CORE_PORT: String(instance.ports.restApi),
    ROTKI_INSTANCE_COLIBRI_PORT: String(instance.ports.colibri),
    ROTKI_INSTANCE_PROXY_PORT: String(instance.ports.starlingProxy),
    ROTKI_INSTANCE_MCP_PORT: String(instance.ports.mcp),
    ROTKI_INSTANCE_DATA_DIR: instance.dir,
  };
}

/**
 * Env for the electron child: the instance's ports when there is one, plus the
 * dev-proxy port when the proxy is on — that one is independent of instance mode,
 * since a plain `pnpm dev` can enable the proxy too.
 */
function envForElectron(instance: InstanceRuntime | null, useProxy: boolean): Record<string, string> | undefined {
  const env: Record<string, string> = { ...instanceEnvForElectron(instance) };
  if (useProxy)
    env.ROTKI_DEV_CORE_UPSTREAM_PORT = String(devProxyPort(instance));

  return Object.keys(env).length > 0 ? env : undefined;
}

function pointFrontendAtBackend(backendEnv: StarlingDevEnv): void {
  // Vite talks to starling's proxy, the same single origin the packaged renderer
  // uses, whether or not the dev-proxy is enabled — with it on, starling routes
  // `/api/1/*` through it upstream, which the renderer never sees. Core answers
  // `/api/1/*`, colibri `/colibri/*`, and the CORS allowance starling passes both
  // backends permits the Vite origin.
  process.env.VITE_BACKEND_URL = backendEnv.VITE_BACKEND_URL;
}

export async function startDevelopmentEnvironment(opts: DevEnvironmentOptions): Promise<void> {
  const { instance, noElectron, useProxy, onChildExit } = opts;

  let backendEnv: StarlingDevEnv | undefined;
  let devPort: number | undefined;
  let extraEnv: Record<string, string> | undefined;

  if (noElectron) {
    let corePort: number;
    ({ backendEnv, corePort, devPort } = await startBackendForMode(instance, opts));
    pointFrontendAtBackend(backendEnv);
    if (useProxy)
      spawnProxyForBackend(instance, corePort);
  }
  else {
    // Electron mode: electron's main process spawns its own backend + colibri.
    // In instance mode hand it the instance's reserved ports + data dir so it
    // binds there rather than on the shared defaults, and run the Vite dev
    // server on the instance's dev port (electron loads that origin). Plain
    // `pnpm dev` leaves devPort undefined, keeping the default 8080.
    extraEnv = envForElectron(instance, useProxy);
    devPort = instance?.ports.dev;
    if (useProxy) {
      await assertDevProxyPortFree(devProxyPort(instance));
      spawnProxyForElectron(instance);
    }
  }

  startDevServer({ noElectron, devPort, backendEnv, extraEnv, onExit: onChildExit });

  // win32 historically had no readiness wait — give hot-reload subscribers a
  // moment to attach before the first Vite compile.
  if (noElectron && platform() === 'win32') {
    await new Promise(resolve => setTimeout(resolve, 1_000));
  }
}
