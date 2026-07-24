import type { AppConfig } from '@electron/main/app-config';
import type { LogService } from '@electron/main/log-service';
import type { JsonRpcResponse, StarlingErrorListener } from '@electron/main/starling-handler-types';
import { type ChildProcess, spawn } from 'node:child_process';
import * as os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import readline from 'node:readline';
import { selectPort } from '@electron/main/port-utils';
import { resolveLogLevel } from '@electron/main/resolve-log-level';
import { buildStarlingInvocation, SHUTDOWN_GRACE_SECS, type StarlingInvocation } from '@electron/main/starling-args';
import { forwardStarlingLine } from '@electron/main/starling-log';
import { eventLastError, getMcpServerState, isMcpCrash, setMcpServerRunning } from '@electron/main/starling-mcp';
import { BackendCode, type BackendOptions, type McpServiceState } from '@shared/ipc';
import { wait } from '@shared/utils';

/** starling exits with this code when the data dir is already locked (main.rs). */
const EXIT_DATADIR_IN_USE = 3;
const API_HOST = '127.0.0.1';

/**
 * How long `stop` may take to answer: starling only replies once the backend tree
 * is down, which it gives itself `SHUTDOWN_GRACE_SECS` to do. Anything shorter
 * gives up on a shutdown that is still going fine.
 */
const STOP_REQUEST_TIMEOUT = SHUTDOWN_GRACE_SECS * 1000;

/** Time starling gets to exit itself once the grace elapsed, before SIGKILL. */
const EXIT_MARGIN = 5_000;

/**
 * Owns the single `starling` supervisor child and the control RPC over its
 * stdio. Replaces the old SubprocessHandler + two ProcessManagers: starling now
 * spawns/supervises/tree-kills core + colibri, and this class drives it.
 *
 * The renderer talks directly to the loopback URLs this handler fills in from
 * the ports it allocates before spawning. No reverse proxy is involved.
 */
export class StarlingHandler {
  private child: ChildProcess | undefined;
  private exiting: boolean = false;
  /** Resolved on the child's `exit`, with its exit code (or null on signal). */
  private exited: Promise<number | null> | undefined;
  /** Data/log dirs the running child was started with, to detect a switch. */
  private currentDataDir: string | undefined;
  private currentLogDir: string | undefined;

  // --- JSON-RPC client state ---
  private nextId: number = 1;
  private readonly pending = new Map<number, { resolve: (value: any) => void; reject: (error: Error) => void }>();

  constructor(private readonly logger: LogService, private readonly config: AppConfig) {
    this.logger.info('Starting rotki (starling supervisor)');
  }

  private checkIfMacOsVersionIsSupported(): boolean {
    if (os.platform() !== 'darwin')
      return true;
    const majorVersion = Number.parseInt(os.release().split('.')[0]);
    return !(majorVersion < 17);
  }

  private checkIfWindowsVersionIsSupported(): boolean {
    if (os.platform() !== 'win32')
      return true;
    const parts = os.release().split('.');
    if (parts.length > 1) {
      const windowsVersion = Number.parseInt(parts[0]) + Number.parseInt(parts[1]) * 0.1;
      return windowsVersion >= 6.1;
    }
    return true;
  }

  // Start the backend (first start) or apply a restart: starling is spawned once
  // and reconfigured in place over the control RPC, except a data/log directory
  // switch, which respawns it (the data-dir lock is keyed to the launch dir).
  async restartBackend(options: Partial<BackendOptions>, listener: StarlingErrorListener): Promise<void> {
    if (process.env.SKIP_PYTHON_BACKEND) {
      this.logger.warn('Skipped starting the backend (SKIP_PYTHON_BACKEND)');
      return;
    }

    if (!this.checkIfMacOsVersionIsSupported()) {
      listener.onProcessError('rotki requires at least macOS High Sierra', BackendCode.MACOS_VERSION);
      return;
    }
    if (!this.checkIfWindowsVersionIsSupported()) {
      listener.onProcessError('rotki requires at least Windows 10', BackendCode.WIN_VERSION);
      return;
    }

    const dirsChanged = options.dataDirectory !== this.currentDataDir
      || (options.logDirectory ?? undefined) !== this.currentLogDir;

    if (this.child && !dirsChanged) {
      await this.restartInPlace(options, listener);
    }
    else {
      await this.stop();
      await this.spawnAndGate(options, listener);
    }
  }

  /** Reconfigure-and-restart the live child via the control RPC. */
  private async restartInPlace(options: Partial<BackendOptions>, listener: StarlingErrorListener): Promise<void> {
    this.logger.info('Restarting backend in place via control RPC');
    try {
      await this.request('restart', this.restartParams(options));
    }
    catch (error: any) {
      this.logger.error('Backend restart failed', error);
      listener.onProcessError(error instanceof Error ? error.message : String(error), BackendCode.TERMINATED);
    }
  }

  /**
   * The `restart` RPC params. Every BackendOptions field already maps 1:1 to a
   * camelCase wire field starling accepts, so the set options pass straight
   * through (an absent field leaves that setting unchanged).
   */
  private restartParams(options: Partial<BackendOptions>): Record<string, unknown> {
    const params: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(options)) {
      if (value !== undefined)
        params[key] = value;
    }
    return params;
  }

  /** Allocate ports, spawn the child, then wait for the initial `ready` event. */
  private async spawnAndGate(options: Partial<BackendOptions>, listener: StarlingErrorListener): Promise<void> {
    this.logger.updateLogDirectory(options.logDirectory);
    this.exiting = false;

    const corePort = await this.resolvePort('core');
    const colibriPort = await this.resolvePort('colibri');
    const mcpPort = await this.resolvePort('mcp');
    const logsDir = this.logsDirectory();

    const invocation = buildStarlingInvocation({
      isDev: this.config.isDev,
      corePort,
      colibriPort,
      mcpPort,
      apiHost: API_HOST,
      logsDir,
      options,
    });

    this.spawnChild(invocation, listener);
    this.currentDataDir = options.dataDirectory;
    this.currentLogDir = options.logDirectory;

    // starling boots idle and serves its control channel immediately. Drive the
    // first bring-up with the `start` request, carrying the backend options
    // (log level, tunables, data dir) the CLI no longer passes. It resolves once
    // the whole tree is ready, and rejects on a failed bring-up or early exit.
    try {
      await this.request('start', this.startParams(options));
    }
    catch (error) {
      // Report only while the child is still alive: if it already exited, its
      // `exit` handler reported the precise reason (data-dir lock / non-zero
      // exit) and rejected this request as a side effect — re-reporting doubles it.
      if (!this.exiting && this.child) {
        this.logger.error('Backend start failed', error);
        listener.onProcessError(
          'Failed to start the rotki backend. Please check the logs for more details.',
          BackendCode.TERMINATED,
        );
        await this.stop();
      }
    }
  }

  /**
   * The `start` control params: the same BackendOptions shape a restart sends,
   * plus an explicit resolved log level so the initial bring-up uses the right
   * default (debug in dev, the persisted/critical level in prod) rather than the
   * supervisor's boot default.
   */
  private startParams(options: Partial<BackendOptions>): Record<string, unknown> {
    return {
      ...this.restartParams(options),
      loglevel: resolveLogLevel(options.loglevel, this.config.isDev),
    };
  }

  private spawnChild(invocation: StarlingInvocation, listener: StarlingErrorListener): void {
    this.logger.info(`Spawning starling: ${invocation.command} ${invocation.args.join(' ')}`);
    const child = spawn(invocation.command, invocation.args, {
      cwd: invocation.cwd,
      // A complete env, not an overlay: spreading it over `process.env` would hand
      // a Windows child both `Path` and `PATH` and let it pick. See StarlingInvocation.
      env: invocation.env ?? process.env,
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    this.child = child;

    if (!child.stdout || !child.stderr || !child.stdin)
      throw new Error('starling child is missing its stdio pipes');

    // stdout is the NDJSON control channel (responses + event notifications).
    const rl = readline.createInterface({ input: child.stdout });
    rl.on('line', line => this.onLine(line, listener));

    // stderr carries starling's own logs and the inherited backend stderr, so
    // supervisor diagnostics land in the Electron log (gotcha 2).
    const errReader = readline.createInterface({ input: child.stderr });
    errReader.on('line', line => forwardStarlingLine(this.logger, line));

    child.on('error', (error) => {
      this.logger.error('Failed to spawn starling', error);
      if (!this.exiting)
        listener.onProcessError(error, BackendCode.TERMINATED);
    });

    this.exited = new Promise<number | null>((resolve) => {
      child.on('exit', (code, signal) => {
        this.logger.info(`starling exited (code: ${code}, signal: ${signal})`);
        rl.close();
        errReader.close();
        // Rejecting the pending requests also unblocks the initial `start`
        // request if the child died before replying.
        this.rejectAllPending(new Error('starling exited'));
        this.child = undefined;
        if (!this.exiting && code === EXIT_DATADIR_IN_USE) {
          listener.onProcessError(
            'Another rotki instance is already using this data directory. Please close it and try again.',
            BackendCode.TERMINATED,
          );
        }
        else if (!this.exiting && code !== 0) {
          listener.onProcessError(
            'The rotki backend stopped unexpectedly. Please check the logs for more details.',
            BackendCode.TERMINATED,
          );
        }
        resolve(code);
      });
    });
  }

  /** Parse one NDJSON line: an id-correlated response, or an event notification. */
  private onLine(line: string, listener: StarlingErrorListener): void {
    const trimmed = line.trim();
    if (!trimmed)
      return;
    let message: JsonRpcResponse;
    try {
      message = JSON.parse(trimmed);
    }
    catch {
      this.logger.warn(`Ignoring non-JSON line from starling: ${trimmed}`);
      return;
    }

    if (typeof message.id === 'number') {
      const pending = this.pending.get(message.id);
      if (!pending)
        return;
      this.pending.delete(message.id);
      if (message.error)
        pending.reject(new Error(message.error.message));
      else
        pending.resolve(message.result);
      return;
    }

    if (message.method)
      this.onEvent(message.method, message.params, listener);
  }

  private onEvent(method: string, params: unknown, listener: StarlingErrorListener): void {
    switch (method) {
      case 'event.ready':
        // The whole backend tree is up. Initial readiness is gated on the `start`
        // request's reply, not this event, so this is purely informational (it
        // also fires after a restart brings the tree back up).
        this.logger.info('Backend event: event.ready');
        break;
      case 'event.crashed': {
        const lastError = eventLastError(params);
        this.logger.error(`Backend service crashed: ${lastError}`);
        if (isMcpCrash(params))
          listener.onMcpState?.('Failed');
        else if (!this.exiting)
          listener.onProcessError(lastError, BackendCode.TERMINATED);
        break;
      }
      case 'event.restarting':
      case 'event.stopped':
        this.logger.info(`Backend event: ${method}`);
        break;
      default:
        this.logger.debug(`Unhandled control event: ${method}`);
    }
  }

  async getMcpServerState(): Promise<McpServiceState> {
    return this.child
      ? getMcpServerState(async (method, params) => this.request(method, params))
      : 'Unavailable';
  }

  getMcpServerEndpoint(): string {
    return `http://${API_HOST}:${this.config.ports.mcpPort}/mcp`;
  }

  async setMcpServerRunning(running: boolean): Promise<McpServiceState> {
    return this.child
      ? setMcpServerRunning(async (method, params) => this.request(method, params), running)
      : 'Unavailable';
  }

  /** Send a JSON-RPC request over the child's stdin and await its response. */
  private async request<T = unknown>(method: string, params?: Record<string, unknown>): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      const child = this.child;
      if (!child?.stdin) {
        reject(new Error('starling is not running'));
        return;
      }
      const id = this.nextId++;
      this.pending.set(id, { resolve, reject });
      const payload = JSON.stringify({ jsonrpc: '2.0', id, method, ...(params ? { params } : {}) });
      child.stdin.write(`${payload}\n`, (error) => {
        if (error) {
          this.pending.delete(id);
          reject(error);
        }
      });
    });
  }

  private rejectAllPending(error: Error): void {
    for (const { reject } of this.pending.values())
      reject(error);
    this.pending.clear();
  }

  /**
   * Stop the running child: ask it to shut the backend tree down gracefully via
   * `stop`, then wait for exit (killing it if it does not go). starling does the
   * ordered teardown + Windows Job Objects, so there is no taskkill/ps-list here.
   *
   * Both waits are derived from the grace we hand starling on the CLI: killing it
   * before its own escalation has run leaves the backends it was reaping orphaned,
   * which is exactly what starling exists to prevent.
   */
  async stop(): Promise<void> {
    const child = this.child;
    if (!child)
      return;

    this.exiting = true;
    this.logger.debug('Stopping starling');
    try {
      await Promise.race([this.request('stop').catch(() => undefined), wait(STOP_REQUEST_TIMEOUT)]);
    }
    catch {
      // best-effort; fall through to wait/kill
    }

    if (this.child) {
      const exited = this.exited ?? Promise.resolve(null);
      const timedOut = await Promise.race([exited.then(() => false), wait(EXIT_MARGIN).then(() => true)]);
      if (timedOut && this.child) {
        this.logger.warn('starling did not exit in time, killing it');
        this.child.kill('SIGKILL');
      }
    }
    this.child = undefined;
    this.exiting = false;
  }

  private logsDirectory(): string {
    // LogService writes the per-process logfiles here; starling needs the dir.
    return path.dirname(this.logger.coreProcessLogPath);
  }

  /**
   * Allocate a free loopback port for a service from its configured default and
   * publish the resulting origin the renderer dials directly.
   */
  private async resolvePort(name: 'core' | 'colibri' | 'mcp'): Promise<number> {
    const defaultPort = this.config.ports[`${name}Port`];
    const port = await selectPort(defaultPort, API_HOST);
    if (port !== defaultPort)
      this.logger.warn(`Using non-default port ${port} for ${name}`);
    const url = `http://${API_HOST}:${port}`;
    if (name === 'core')
      this.config.urls.coreApiUrl = url;
    else if (name === 'colibri')
      this.config.urls.colibriApiUrl = url;
    else
      this.config.ports.mcpPort = port;
    return port;
  }
}
