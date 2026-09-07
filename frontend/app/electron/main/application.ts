import type { AppConfig } from '@electron/main/app-config';
import type { McpServerStatus, StarlingServiceStatus } from '@shared/ipc';
import process from 'node:process';
import { IpcCommands } from '@electron/ipc-commands';
import { protectHtmlAssociation } from '@electron/main/html-mime-protection';
import { IpcManager } from '@electron/main/ipc-setup';
import { LogService } from '@electron/main/log-service';
import { MenuManager } from '@electron/main/menu';
import { parseToken } from '@electron/main/oauth-utils';
import { resolveLogLevel } from '@electron/main/resolve-log-level';
import { SettingsManager } from '@electron/main/settings-manager';
import { StarlingHandler } from '@electron/main/starling-handler';
import { TrayManager } from '@electron/main/tray-manager';
import { WindowManager } from '@electron/main/window-manager';
import { DEFAULT_COLIBRI_PORT, DEFAULT_MCP_PORT, DEFAULT_PORT, DEFAULT_PROXY_PORT } from '@shared/port-utils';
import { checkIfDevelopment, startPromise } from '@shared/utils';
import { app, protocol } from 'electron';

/**
 * Reads a dev-instance port override from the environment. `start-dev` sets
 * these only when running an isolated instance so electron binds its backend +
 * colibri on the instance's reserved ports instead of the shared defaults.
 * Falls back to the default when unset or malformed.
 */
function instancePort(envKey: string, fallback: number): number {
  const raw = process.env[envKey];
  if (!raw)
    return fallback;
  const port = Number.parseInt(raw, 10);
  return Number.isFinite(port) && port > 0 ? port : fallback;
}

/** A port that is meaningful only by its presence, so absence stays undefined. */
function optionalPort(envKey: string): number | undefined {
  const raw = process.env[envKey];
  if (!raw)
    return undefined;
  const port = Number.parseInt(raw, 10);
  return Number.isFinite(port) && port > 0 ? port : undefined;
}

export class Application {
  private readonly window: WindowManager;
  private readonly tray: TrayManager;
  private readonly ipc: IpcManager;
  private readonly logger: LogService;
  private readonly processHandler: StarlingHandler;
  private readonly menu: MenuManager;
  private readonly settings: SettingsManager;
  private protocolRegistrationFailed: boolean = false;
  private readonly appConfig: AppConfig = {
    isDev: checkIfDevelopment(),
    isMac: process.platform === 'darwin',
    apiUrl: import.meta.env.VITE_BACKEND_URL,
    ports: {
      colibriPort: instancePort('ROTKI_INSTANCE_COLIBRI_PORT', DEFAULT_COLIBRI_PORT),
      corePort: instancePort('ROTKI_INSTANCE_CORE_PORT', DEFAULT_PORT),
      mcpPort: instancePort('ROTKI_INSTANCE_MCP_PORT', DEFAULT_MCP_PORT),
      proxyPort: instancePort('ROTKI_INSTANCE_PROXY_PORT', DEFAULT_PROXY_PORT),
      // No fallback: absent means no dev-proxy, so starling stays pointed at core.
      coreUpstreamPort: optionalPort('ROTKI_DEV_CORE_UPSTREAM_PORT'),
    },
  };

  constructor() {
    this.logger = new LogService(app);
    this.logger.setLogLevel(resolveLogLevel(undefined, this.appConfig.isDev));
    this.settings = new SettingsManager(app);
    this.processHandler = new StarlingHandler(this.logger, this.appConfig);
    this.window = new WindowManager(this.logger);
    this.menu = new MenuManager(this.logger, this.settings, this.appConfig);
    this.tray = new TrayManager(this.settings, this.appConfig);
    this.ipc = new IpcManager(this.logger, this.settings, this.appConfig);
  }

  async start(): Promise<void> {
    const lock = app.requestSingleInstanceLock();

    if (!lock) {
      app.quit();
      return;
    }

    this.setupAppEvents();
    this.registerAppProtocols();
    await app.whenReady();
    await this.initialize();
  }

  private registerAppProtocols() {
    // Standard scheme must be registered before the app is ready
    protocol.registerSchemesAsPrivileged([
      {
        scheme: 'app',
        privileges: { standard: true, secure: true, supportFetchAPI: true },
      },
      {
        scheme: 'rotki',
        privileges: { standard: true, secure: true },
      },
    ]);
  }

  private handleProtocolUrl(commandLine: string[]): void {
    const rotkiUrl = commandLine.find(arg => arg.startsWith('rotki://'));

    if (rotkiUrl) {
      this.window.sendOAuthCallback(parseToken(rotkiUrl));
    }
  }

  /** Guarded because registering a URL scheme can hijack the text/html association (#12323). */
  private registerAsDefaultProtocolHandler() {
    protectHtmlAssociation(this.logger, () => this.registerProtocolClient());
  }

  private registerProtocolClient(): boolean {
    if (process.defaultApp) {
      /* Dev always re-registers so rotki:// points at the current binary. Guarding on
         isDefaultProtocolClient would skip wrongly: on Linux it ignores the path and args. */
      if (process.argv.length < 2)
        return false;

      const devArgs = [process.argv[1]];
      this.logger.info(`Registering ${process.execPath} ${process.argv[1]} as the default handler for rotki:// protocol`);
      const registrationSuccess = app.setAsDefaultProtocolClient('rotki', process.execPath, devArgs);
      if (!registrationSuccess) {
        this.protocolRegistrationFailed = true;
        this.logger.warn(`Failed to register ${process.execPath} ${process.argv[1]} as the default handler for rotki:// protocol`);
      }
      return true;
    }

    // Production: already the default, so the destructive xdg-settings call is not re-run.
    if (app.isDefaultProtocolClient('rotki')) {
      this.logger.info('rotki:// protocol handler already registered; skipping');
      return false;
    }

    this.logger.info(`Registering the app as the default handler for rotki:// protocol`);
    const registrationSuccess = app.setAsDefaultProtocolClient('rotki');
    if (!registrationSuccess) {
      this.protocolRegistrationFailed = true;
      this.logger.warn(`Failed to register the app as the default handler for rotki:// protocol`);
    }
    return true;
  }

  private async initialize() {
    this.registerAsDefaultProtocolHandler();

    // Clear OAuth cookies on startup to ensure clean state between users
    this.ipc.clearOAuthCookiesOnStartup();

    // Handle protocol URL if app was opened with one
    if (process.argv.length >= 2) {
      this.handleProtocolUrl(process.argv);
    }

    this.menu.initialize({
      onDisplayTrayChanged: (displayTray) => {
        if (displayTray)
          this.tray.build();
        else
          this.tray.cleanup();
      },
    },

    );
    this.ipc.initialize({
      quit: this.quit.bind(this),
      updateTray: params => this.tray.update(params),
      updatePremiumMenu: isPremium => this.menu.updatePremiumStatus(isPremium),
      setDataDirectory: dataDirectory => this.menu.setDataDirectory(dataDirectory),
      restartSubprocesses: async (options) => {
        this.logger.setLogLevel(resolveLogLevel(options.loglevel, this.appConfig.isDev));
        await this.processHandler.restartBackend({
          ...options,
          mcpAutoStart: this.settings.appSettings.mcpAutoStart,
        }, {
          onMcpState: state => this.window.sendIpcMessage(IpcCommands.MCP_STATE, state),
          onProcessError: (message, code) => this.window.setStartupError(message, code),
        });
      },
      terminateSubprocesses: async (update = false) => {
        if (update) {
          this.window.cleanup();
          this.cleanup();
        }
        await this.processHandler.stop();
      },
      updateDownloadProgress: progress => this.window.updateProgress(progress),
      getProtocolRegistrationFailed: () => this.protocolRegistrationFailed,
      openOAuthInWindow: async (url: string) => this.window.openOAuthWindow(url),
      sendIpcMessage: (channel: string, ...args: any[]) => this.window.sendIpcMessage(channel, ...args),
      getMcpServerStatus: async () => this.getMcpServerStatus(),
      setMcpAutoStart: async (enabled: boolean) => {
        this.settings.setMcpAutoStart(enabled);
        return this.getMcpServerStatus();
      },
      startMcpServer: async () => this.getMcpServerStatus(await this.processHandler.setMcpServerRunning(true)),
      stopMcpServer: async () => this.getMcpServerStatus(await this.processHandler.setMcpServerRunning(false)),
      resetMcpSession: async () => this.processHandler.resetMcpSession(),
    });
    await this.window.create();
    this.window.setListener({
      quit: () => startPromise(this.quit()),
      onWindowVisibilityChanged: visible => this.tray.updateContextMenu(visible),
    });
    this.tray.initialize({
      quit: () => startPromise(this.quit()),
      toggleWindowVisibility: () => this.window.toggleVisibility(),
    });
  }

  private async getMcpServerStatus(state?: StarlingServiceStatus): Promise<McpServerStatus> {
    return {
      autoStart: this.settings.appSettings.mcpAutoStart,
      endpoint: this.processHandler.getMcpServerEndpoint(),
      state: state ?? await this.processHandler.getMcpServerState(),
    };
  }

  private setupAppEvents() {
    app.on('second-instance', (_event, commandLine, _workingDirectory) => {
      // Handle protocol URL when app is already running
      this.handleProtocolUrl(commandLine);
      this.window.focus();
    });

    app.on('open-url', (event, url) => {
      // Handle protocol URL on macOS
      event.preventDefault();
      this.handleProtocolUrl([url]);
    });

    app.on('window-all-closed', (): void => {
      if (!this.appConfig.isMac)
        app.quit();
    });
    app.on('activate', () => startPromise(this.window.activate()));
    app.on('will-quit', (e) => {
      e.preventDefault();
      startPromise(this.quit());
    });
    app.on('before-quit', (): void => this.window.forceClose());
  }

  private cleanup() {
    app.removeAllListeners('second-instance');
    app.removeAllListeners('open-url');
    app.removeAllListeners('window-all-closed');
    app.removeAllListeners('activate');
    app.removeAllListeners('will-quit');
    app.removeAllListeners('before-quit');
  }

  /**
   * Tears the app down in an order the renderer can survive.
   *
   * @remarks
   * The renderer is told first so it can swap in the shutdown screen, which unmounts the
   * notification popup: requests unwinding against the dying backend then cannot surface errors
   * over a closing window. The window is destroyed only after the backend is down, since it holds
   * that screen, and the IPC handlers are dropped last because the renderer keeps invoking them
   * throughout, provider detection among others.
   */
  private async quit() {
    this.window.notifyClosing();

    this.cleanup();
    this.menu.cleanup();
    this.tray.cleanup();
    try {
      await this.processHandler.stop();
    }
    finally {
      this.window.destroy();
      await this.ipc.cleanup();

      // `will-quit` preventDefault()s, so this is the only thing that ends the process.
      try {
        app.exit();
      }
      catch (error: any) {
        if (error.message !== 'Object has been destroyed')
          console.error(error);
      }
    }
  }
}
