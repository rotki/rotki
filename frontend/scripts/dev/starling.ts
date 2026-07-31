import path from 'node:path';
import process from 'node:process';
import { DEFAULT_MCP_PORT, DEFAULT_PROXY_PORT, selectPort } from '../../app/shared/port-utils';
import { buildStarlingInvocation, SHUTDOWN_GRACE_SECS, type StarlingBackendOptions } from '../../app/shared/starling/starling-args';
import { requestStarlingStart, spawnStarling } from '../../app/shared/starling/starling-launch';
import { StarlingRpc } from '../../app/shared/starling/starling-rpc';
import { createDevLogger, formatDevLine } from './logger';
import { registerShutdownHook } from './process-pool';

const logger = createDevLogger('dev:starling');

const API_HOST = '127.0.0.1';

/** How long `stop` may take: starling only answers once the tree is down. */
const STOP_REQUEST_TIMEOUT_MS = SHUTDOWN_GRACE_SECS * 1000;

export interface StarlingDevOptions {
  logDir: string;
  dataDir?: string;
  /** Port core binds, or starts probing from when `strictPorts` is false. */
  corePort: number;
  /** Port colibri binds, or starts probing from when `strictPorts` is false. */
  colibriPort: number;
  /**
   * Bind the given core/colibri ports exactly rather than probing upward. Set
   * for `--instance` runs, which reserve a slot and must land on it.
   */
  strictPorts: boolean;
}

export interface StarlingDevEnv {
  /** The single origin the renderer talks to: starling's reverse proxy. */
  VITE_BACKEND_URL: string;
  VITE_COLIBRI_URL: string;
}

async function wait(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Start the backend tree the same way Electron does: spawn the starling
 * supervisor, then drive the first bring-up with a `start` request over its
 * stdio control channel. starling spawns and supervises core and colibri, and
 * fronts both behind its reverse proxy, so web dev reaches them through one
 * origin exactly as the desktop app does.
 *
 * The `start` request is the readiness gate — it resolves only once the whole
 * tree is up — so there is nothing here to poll.
 */
export async function startStarlingSupervisor(options: StarlingDevOptions): Promise<StarlingDevEnv> {
  const corePort = options.strictPorts ? options.corePort : await selectPort(options.corePort, API_HOST);
  const colibriPort = options.strictPorts ? options.colibriPort : await selectPort(options.colibriPort, API_HOST);
  // The two ports the caller does not choose come from the same defaults the
  // Electron main process uses. Both are probed, so a busy default walks up,
  // which is how two concurrent dev:web runs stay off each other without
  // reserving a slot in the instance port registry.
  const mcpPort = await selectPort(DEFAULT_MCP_PORT, API_HOST);
  const proxyPort = await selectPort(DEFAULT_PROXY_PORT, API_HOST);

  const backendOptions: StarlingBackendOptions = {
    logDirectory: options.logDir,
    ...(options.dataDir ? { dataDirectory: options.dataDir } : {}),
  };

  const invocation = buildStarlingInvocation({
    isDev: true,
    corePort,
    colibriPort,
    mcpPort,
    proxyPort,
    apiHost: API_HOST,
    logsDir: options.logDir,
    options: backendOptions,
    // serve.ts exports this before Vite boots, so it is only set for a dev
    // server started earlier in this process tree; undefined falls back to the
    // `http://localhost:*` allowance, which covers the default web-dev origin.
    devServerUrl: process.env.VITE_DEV_SERVER_URL,
    // The dev scripts run from `frontend`, Electron from `frontend/app`, so the
    // default two-levels-up would land above the repo.
    repoRoot: path.resolve(process.cwd(), '..'),
  });

  logger.info(`Starting starling supervisor (proxy on ${proxyPort}, core ${corePort}, colibri ${colibriPort})`);

  const rpc = new StarlingRpc({ warn: message => logger.warn(message) }, (method) => {
    // The `start` reply is the readiness gate, so events are informational here;
    // a crash still needs surfacing because it can arrive long after startup.
    if (method === 'event.crashed')
      logger.error('a backend service crashed — see the starling output above');
    else
      logger.info(`starling event: ${method}`);
  });

  const { child, exited } = spawnStarling({
    invocation,
    rpc,
    // starling's stderr carries its own logs plus the inherited core/colibri
    // stderr, which is the only place those surface in web dev.
    onStderr: line => process.stdout.write(`${formatDevLine('starling', line)}\n`),
  });

  child.on('error', error => logger.error(`failed to spawn starling: ${error.message}`));

  let stopping = false;
  registerShutdownHook(async () => {
    if (stopping || child.exitCode !== null)
      return;
    stopping = true;
    logger.info('stopping starling');
    // Ask for the ordered teardown, then outwait the grace starling gives its
    // own children. Killing it earlier orphans the very processes it reaps.
    await Promise.race([rpc.request('stop').catch(() => undefined), wait(STOP_REQUEST_TIMEOUT_MS)]);
    if (child.exitCode === null)
      child.kill('SIGKILL');
  });

  // A supervisor that dies before `start` replies rejects the request below, but
  // one that dies later would otherwise leave the dev server pointed at nothing.
  exited.then(({ code, signal }) => {
    if (!stopping)
      logger.error(`starling exited unexpectedly (code: ${code}, signal: ${signal})`);
  }).catch(() => undefined);

  try {
    await requestStarlingStart(rpc, backendOptions, 'debug');
  }
  catch (error) {
    child.kill('SIGKILL');
    const reason = error instanceof Error ? error.message : String(error);
    throw new Error(`starling failed to bring up the backend services: ${reason}`);
  }

  const proxyOrigin = `http://${API_HOST}:${proxyPort}`;
  logger.info(`backend services ready behind ${proxyOrigin}`);
  return {
    VITE_BACKEND_URL: proxyOrigin,
    VITE_COLIBRI_URL: `${proxyOrigin}/colibri`,
  };
}
