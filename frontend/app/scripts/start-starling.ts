import path from 'node:path';
import process from 'node:process';
import { cac } from 'cac';
import consola from 'consola';
import { buildStarlingInvocation, SHUTDOWN_GRACE_SECS, type StarlingBackendOptions, type StarlingInvocation } from '../shared/starling/starling-args';
import { requestStarlingStart, spawnStarling } from '../shared/starling/starling-launch';
import { StarlingRpc } from '../shared/starling/starling-rpc';

/**
 * Starts the whole backend tree for the e2e run: starling supervises core and
 * colibri and fronts both behind its reverse proxy, so the tests address one
 * origin, exactly as the desktop app and `dev:web` do. Replaces the separate
 * start-backend/start-colibri scripts, which spawned the two services directly
 * and left the suite exercising a two-origin topology no shipping mode uses.
 *
 * starling boots idle and is brought up with a `start` control request, whose
 * reply resolves only once both services are ready — so Playwright's `url` probe
 * finds the proxy already answering rather than racing it.
 */
interface StarlingE2eOptions {
  data: string;
  logs: string;
  /** Port the reverse proxy binds — the single origin the tests address. */
  port: number;
  corePort: number;
  colibriPort: number;
  mcpPort: number;
}

const API_HOST = '127.0.0.1';

/** Repo root: this file sits at `frontend/app/scripts`. */
function repoRoot(): string {
  return path.join(import.meta.dirname, '..', '..', '..');
}

/**
 * `buildStarlingInvocation` resolves the whole tree: the prebuilt starling and
 * colibri binaries when they exist, `cargo run` only when neither profile has
 * them. CI ships the release binaries from the build job and has no cargo, so
 * that first branch is the one that has to hit there.
 */
function resolveInvocation(options: StarlingE2eOptions, root: string): StarlingInvocation {
  const backendOptions: StarlingBackendOptions = {
    dataDirectory: options.data,
    logDirectory: options.logs,
  };

  const invocation = buildStarlingInvocation({
    isDev: true,
    corePort: options.corePort,
    colibriPort: options.colibriPort,
    mcpPort: options.mcpPort,
    proxyPort: options.port,
    apiHost: API_HOST,
    logsDir: options.logs,
    options: backendOptions,
    repoRoot: root,
    // The suite drives every query itself; background refreshes would race it.
    disableTaskManager: true,
  });

  return invocation;
}

async function startStarling(options: StarlingE2eOptions): Promise<void> {
  const root = repoRoot();
  const invocation = resolveInvocation(options, root);
  consola.info(`Starting starling (proxy ${options.port}, core ${options.corePort}, colibri ${options.colibriPort}) via ${invocation.command}`);

  const rpc = new StarlingRpc({ warn: message => consola.warn(message) }, (method) => {
    if (method === 'event.crashed')
      consola.error('a backend service crashed');
  });

  const { child, exited } = spawnStarling({
    invocation,
    rpc,
    // starling's own logs plus the inherited core/colibri stderr. Playwright
    // captures this and the workflow uploads it with the run artifacts.
    onStderr: line => process.stderr.write(`${line}\n`),
  });

  let stopping = false;

  function cleanup(signal: string): void {
    if (stopping)
      return;
    stopping = true;
    consola.info(`Received ${signal}, stopping starling...`);
    // Ask for the ordered teardown and let starling tree-kill core and colibri
    // itself: they run in their own process groups, so nothing else reaches them
    // and killing the supervisor early strands both. Escalate only once its own
    // grace has elapsed. The `exited` await below holds this process open until
    // the tree is actually down.
    rpc.request('stop').catch(() => undefined);
    setTimeout(() => {
      if (child.exitCode === null) {
        consola.warn('starling did not exit within its grace period, killing it');
        child.kill('SIGKILL');
      }
    }, SHUTDOWN_GRACE_SECS * 1000);
  }

  process.on('SIGTERM', () => cleanup('SIGTERM'));
  process.on('SIGINT', () => cleanup('SIGINT'));
  process.on('SIGHUP', () => cleanup('SIGHUP'));

  child.on('error', (error) => {
    consola.error(`Failed to spawn starling: ${error.message}`);
    process.exit(1);
  });

  try {
    await requestStarlingStart(rpc, {
      dataDirectory: options.data,
      logDirectory: options.logs,
    }, 'debug');
  }
  catch (error) {
    consola.error(`starling failed to start the backend services: ${error instanceof Error ? error.message : String(error)}`);
    child.kill('SIGKILL');
    process.exit(1);
  }

  consola.success(`Backend services ready behind http://${API_HOST}:${options.port}`);

  // Stay alive for the run: Playwright owns this process and signals it on
  // teardown. Exit with the supervisor so a crash fails the run loudly.
  const { code } = await exited;
  consola.info(`starling exited with code ${code}`);
  process.exit(code ?? 0);
}

const cli = cac();

cli.command('', 'Start the rotki backend tree under the starling supervisor')
  .option('--data <dir>', 'Data directory')
  .option('--logs <dir>', 'Logs directory')
  .option('--port <port>', 'Proxy port (the single origin the tests address)')
  .option('--core-port <port>', 'Port for the core REST API')
  .option('--colibri-port <port>', 'Port for colibri')
  .option('--mcp-port <port>', 'Port for the MCP server')
  .action(async (options) => {
    const required = ['data', 'logs', 'port', 'corePort', 'colibriPort', 'mcpPort'];
    const missing = required.filter(key => !options[key]);
    if (missing.length > 0) {
      consola.error(`Missing required options: ${missing.map(key => `--${key}`).join(', ')}`);
      process.exit(1);
    }
    await startStarling({
      data: options.data,
      logs: options.logs,
      port: Number(options.port),
      corePort: Number(options.corePort),
      colibriPort: Number(options.colibriPort),
      mcpPort: Number(options.mcpPort),
    });
  });

cli.help();
cli.parse();
