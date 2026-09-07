import type { AppConfig } from '@electron/main/app-config';
import type { LogService } from '@electron/main/log-service';
import type { StarlingErrorListener } from '@electron/main/starling-handler-types';
import type { ChildProcess } from 'node:child_process';
import * as os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { resolveLogLevel } from '@electron/main/resolve-log-level';
import { forwardStarlingLine } from '@electron/main/starling-log';
import { eventLastError, getMcpServerState, isMcpCrash, isServiceLive, setMcpServerRunning } from '@electron/main/starling-mcp';
import { BackendCode, type BackendOptions, StarlingServiceStatus } from '@shared/ipc';
import { selectPort } from '@shared/port-utils';
import { buildStarlingInvocation, SHUTDOWN_GRACE_SECS, type StarlingInvocation } from '@shared/starling/starling-args';
import { definedOptions, spawnStarling, stopStarling } from '@shared/starling/starling-launch';
import { StarlingEvent, StarlingMethod, StarlingService } from '@shared/starling/starling-protocol';
import { StarlingRpc } from '@shared/starling/starling-rpc';

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
 * The renderer talks to a single loopback origin: starling's in-process reverse
 * proxy, which this handler binds on an allocated port and forwards to the core
 * and colibri ports it also allocated.
 */
export class StarlingHandler {
  private child: ChildProcess | undefined;
  private exiting: boolean = false;
  /** Resolved on the child's `exit`, with its exit code (or null on signal). */
  private exited: Promise<number | null> | undefined;
  /** Data/log dirs the running child was started with, to detect a switch. */
  private currentDataDir: string | undefined;
  private currentLogDir: string | undefined;

  /** The listener for the live child, so control-channel events can reach it. */
  private currentListener: StarlingErrorListener | undefined;

  /** The NDJSON JSON-RPC client over the child's stdio. */
  private readonly rpc: StarlingRpc;

  constructor(private readonly logger: LogService, private readonly config: AppConfig) {
    this.logger.info('Starting rotki (starling supervisor)');
    this.rpc = new StarlingRpc(logger, (method, params) => this.onEvent(method, params));
  }

  private checkIfMacOsVersionIsSupported(): boolean {
    if (os.platform() !== 'darwin')
      return true;
    const release = os.release();
    const minorStart = release.indexOf('.');
    const majorVersion = Number.parseInt(minorStart === -1 ? release : release.slice(0, minorStart));
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

  /**
   * Starts the backend, or applies a restart to a running one. starling is spawned once and
   * reconfigured in place over the control RPC, except for a data or log directory switch, which
   * respawns it: the data-dir lock is keyed to the launch directory.
   */
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
      await this.rpc.request(StarlingMethod.RESTART, this.restartParams(options));
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
    return definedOptions(options);
  }

  /** Allocate ports, spawn the child, then wait for the initial `ready` event. */
  private async spawnAndGate(options: Partial<BackendOptions>, listener: StarlingErrorListener): Promise<void> {
    this.logger.updateLogDirectory(options.logDirectory);
    this.exiting = false;

    const corePort = await this.resolvePort(StarlingService.CORE);
    if (this.refuseCoreThatWouldStrandTheProxy(corePort, listener))
      return;

    const colibriPort = await this.resolvePort(StarlingService.COLIBRI);
    const mcpPort = await this.resolvePort(StarlingService.MCP);
    const proxyPort = await this.resolvePort(StarlingService.PROXY);
    const logsDir = this.logsDirectory();

    this.config.apiUrl = `http://${API_HOST}:${proxyPort}`;

    const invocation = buildStarlingInvocation({
      isDev: this.config.isDev,
      corePort,
      colibriPort,
      mcpPort,
      proxyPort,
      coreUpstreamPort: this.config.ports.coreUpstreamPort,
      apiHost: API_HOST,
      logsDir,
      options,
      devServerUrl: import.meta.env.VITE_DEV_SERVER_URL,
    });

    this.spawnChild(invocation, listener);
    this.currentDataDir = options.dataDirectory;
    this.currentLogDir = options.logDirectory;

    await this.driveInitialStart(options, listener);
  }

  /**
   * Whether core would land somewhere a running dev-proxy cannot follow, reported as a process
   * error when it would.
   *
   * @remarks
   * The dev-proxy is handed core's port when it spawns and cannot learn a new one, so a core that
   * probed upward past a taken port would leave it forwarding `/api/1/*` to a dead port. Refusing
   * is the honest outcome, since the alternative comes up looking healthy and answers nothing.
   */
  private refuseCoreThatWouldStrandTheProxy(corePort: number, listener: StarlingErrorListener): boolean {
    if (this.config.ports.coreUpstreamPort === undefined || corePort === this.config.ports.corePort)
      return false;

    listener.onProcessError(
      `The dev-proxy is forwarding to port ${this.config.ports.corePort}, but that port is taken `
      + `and core would bind ${corePort} instead. Free it, or restart without the dev-proxy `
      + '(unset PREMIUM_COMPONENT_DIR, or pass --no-proxy).',
      BackendCode.TERMINATED,
    );
    return true;
  }

  /**
   * Brings the service tree up over the control channel, reporting a failure to the listener.
   *
   * @remarks
   * starling boots idle, so `start` is what raises the tree, carrying the options the CLI no
   * longer passes; it resolves once the tree is ready and rejects on a failure or an early exit.
   * A rejection is only reported while the child is still alive, because the `exit` handler
   * reports a dead one with a more precise reason. starling's own message is preferred over the
   * generic text, since it carries the dead core's stderr tail.
   */
  private async driveInitialStart(options: Partial<BackendOptions>, listener: StarlingErrorListener): Promise<void> {
    try {
      await this.rpc.request(StarlingMethod.START, this.startParams(options));
    }
    catch (error) {
      if (!this.exiting && this.child) {
        this.logger.error('Backend start failed', error);
        const message = error instanceof Error && error.message.length > 0
          ? error.message
          : 'Failed to start the rotki backend. Please check the logs for more details.';
        listener.onProcessError(message, BackendCode.TERMINATED);
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

    const { child, exited } = spawnStarling({
      invocation,
      rpc: this.rpc,
      onStderr: line => forwardStarlingLine(this.logger, line),
    });
    this.child = child;
    this.currentListener = listener;

    child.on('error', (error) => {
      this.logger.error('Failed to spawn starling', error);
      if (!this.exiting)
        listener.onProcessError(error, BackendCode.TERMINATED);
    });

    this.exited = exited.then(({ code, signal }) => {
      this.logger.info(`starling exited (code: ${code}, signal: ${signal})`);
      this.child = undefined;
      this.currentListener = undefined;
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
      return code;
    });
  }

  /** React to a control-channel notification from starling (an `event.*`). */
  private onEvent(method: string, params: unknown): void {
    const listener = this.currentListener;
    switch (method) {
      case StarlingEvent.READY:
        // Informational: readiness is gated on the `start` reply, and this repeats after a restart.
        this.logger.info('Backend event: event.ready');
        break;
      case StarlingEvent.CRASHED: {
        const lastError = eventLastError(params);
        this.logger.error(`Backend service crashed: ${lastError}`);
        if (isMcpCrash(params))
          listener?.onMcpState?.(StarlingServiceStatus.FAILED);
        else if (!this.exiting)
          listener?.onProcessError(lastError, BackendCode.TERMINATED);
        break;
      }
      case StarlingEvent.RESTARTING:
      case StarlingEvent.STOPPED:
        this.logger.info(`Backend event: ${method}`);
        break;
      default:
        this.logger.debug(`Unhandled control event: ${method}`);
    }
  }

  async getMcpServerState(): Promise<StarlingServiceStatus> {
    return this.child
      ? getMcpServerState(async (method, params) => this.rpc.request(method, params))
      : StarlingServiceStatus.UNAVAILABLE;
  }

  getMcpServerEndpoint(): string {
    return `http://${API_HOST}:${this.config.ports.mcpPort}/mcp`;
  }

  async setMcpServerRunning(running: boolean): Promise<StarlingServiceStatus> {
    return this.child
      ? setMcpServerRunning(async (method, params) => this.rpc.request(method, params), running)
      : StarlingServiceStatus.UNAVAILABLE;
  }

  /**
   * Drop data cached by the MCP process and terminate its protocol sessions on user logout.
   * Preserve an intentionally stopped service: only a live MCP process is restarted.
   */
  async resetMcpSession(): Promise<void> {
    if (!isServiceLive(await this.getMcpServerState()))
      return;

    await this.setMcpServerRunning(false);
    await this.setMcpServerRunning(true);
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
    await stopStarling({
      child,
      exited: this.exited ?? Promise.resolve(null),
      exitMarginMs: EXIT_MARGIN,
      logger: {
        debug: message => this.logger.debug(message),
        warn: message => this.logger.warn(message),
      },
      rpc: this.rpc,
      stopTimeoutMs: STOP_REQUEST_TIMEOUT,
    });
    this.child = undefined;
    this.exiting = false;
  }

  /** The directory holding the per-process logfiles, which is what starling takes rather than a path. */
  private logsDirectory(): string {
    return path.dirname(this.logger.coreProcessLogPath);
  }

  /**
   * Allocate a free loopback port for a service from its configured default.
   * The renderer-facing origins are set from the proxy port by the caller; here
   * only `mcp` records its resolved port, which `mcpServerUrl()` reads back.
   */
  private async resolvePort(name: StarlingService): Promise<number> {
    const defaultPort = this.config.ports[`${name}Port`];
    const port = await selectPort(defaultPort, API_HOST);
    if (port !== defaultPort)
      this.logger.warn(`Using non-default port ${port} for ${name}`);
    if (name === StarlingService.MCP)
      this.config.ports.mcpPort = port;
    return port;
  }
}
