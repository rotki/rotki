import path from 'node:path';
import process from 'node:process';
import { selectPort } from '../../app/shared/port-utils';
import { buildStarlingInvocation, SHUTDOWN_GRACE_SECS, type StarlingBackendOptions } from '../../app/shared/starling/starling-args';
import { requestStarlingStart, spawnStarling, stopStarling } from '../../app/shared/starling/starling-launch';
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
  /** Port starling's reverse proxy binds, or starts probing from. */
  proxyPort: number;
  /** Port starling's MCP server binds, or starts probing from. */
  mcpPort: number;
  /**
   * Port of the premium dev-proxy, when it is enabled. starling forwards
   * `/api/1/*` there instead of straight to core, so the proxy can serve locally
   * built premium components without the renderer changing origin.
   */
  coreUpstreamPort?: number;
  /**
   * Bind the given ports exactly rather than probing upward. Set for
   * `--instance` runs, which reserve a slot and must land on it.
   */
  strictPorts: boolean;
}

export interface StarlingDevEnv {
  /** The single origin the renderer talks to: starling's reverse proxy. */
  VITE_BACKEND_URL: string;
}

/** What starling resolved, for callers that need to reach a backend directly. */
export interface StarlingDevPorts {
  /** The port core actually bound, after any probing. */
  corePort: number;
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
export async function startStarlingSupervisor(
  options: StarlingDevOptions,
): Promise<{ env: StarlingDevEnv; ports: StarlingDevPorts }> {
  // In instance mode every port is reserved by the slot, so bind it exactly and
  // fail loudly if something else holds it. Otherwise the caller's values are
  // only a starting point and a busy port walks up, which is how two concurrent
  // plain `dev:web` runs stay off each other without reserving a slot.
  //
  // `selectPort` closes its probe socket before returning and nothing binds
  // until starling spawns, so two services whose start values converge would
  // otherwise be handed the same port (e.g. `--web-port 4141`, which collides
  // with the proxy default). Track what we've handed out and keep walking.
  const taken = new Set<number>();
  const resolve = async (port: number): Promise<number> => {
    if (options.strictPorts) {
      taken.add(port);
      return port;
    }
    let candidate = await selectPort(port, API_HOST);
    while (taken.has(candidate))
      candidate = await selectPort(candidate + 1, API_HOST);
    taken.add(candidate);
    return candidate;
  };

  const corePort = await resolve(options.corePort);
  const colibriPort = await resolve(options.colibriPort);
  const proxyPort = await resolve(options.proxyPort);
  const mcpPort = await resolve(options.mcpPort);

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
    coreUpstreamPort: options.coreUpstreamPort,
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

  const upstreamNote = options.coreUpstreamPort === undefined
    ? ''
    : `, /api/1/* via dev-proxy ${options.coreUpstreamPort}`;
  logger.info(
    `Starting starling supervisor (proxy on ${proxyPort}, core ${corePort}, colibri ${colibriPort}${upstreamNote})`,
  );

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
    // The teardown rule lives in stopStarling. This used to kill as soon as the stop race resolved,
    // which SIGKILLed a supervisor that was still reaping core and colibri.
    await stopStarling({
      child,
      exited,
      logger: { debug: message => logger.info(message), warn: message => logger.warn(message) },
      rpc,
      stopTimeoutMs: STOP_REQUEST_TIMEOUT_MS,
    });
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
    env: { VITE_BACKEND_URL: proxyOrigin },
    ports: { corePort },
  };
}
