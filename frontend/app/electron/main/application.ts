import type { AppConfig } from '@electron/main/app-config';
import process from 'node:process';
import { protectHtmlAssociation } from '@electron/main/html-mime-protection';
import { IpcManager } from '@electron/main/ipc-setup';
import { LogService } from '@electron/main/log-service';
import { MenuManager } from '@electron/main/menu';
import { parseToken } from '@electron/main/oauth-utils';
import { DEFAULT_COLIBRI_PORT, DEFAULT_PORT } from '@electron/main/port-utils';
import { resolveLogLevel } from '@electron/main/resolve-log-level';
import { SettingsManager } from '@electron/main/settings-manager';
import { SubprocessHandler } from '@electron/main/subprocess-handler';
import { TrayManager } from '@electron/main/tray-manager';
import { WindowManager } from '@electron/main/window-manager';
import { checkIfDevelopment, startPromise } from '@shared/utils';
import { app, protocol } from 'electron';

export class Application {
  private readonly window: WindowManager;
  private readonly tray: TrayManager;
  private readonly ipc: IpcManager;
  private readonly logger: LogService;
  private readonly processHandler: SubprocessHandler;
  private readonly menu: MenuManager;
  private readonly settings: SettingsManager;
  private protocolRegistrationFailed: boolean = false;
  private readonly appConfig: AppConfig = {
    isDev: checkIfDevelopment(),
    isMac: process.platform === 'darwin',
    urls: {
      coreApiUrl: import.meta.env.VITE_BACKEND_URL as string,
      colibriApiUrl: import.meta.env.VITE_COLIBRI_URL as string,
    },
    ports: {
      colibriPort: DEFAULT_COLIBRI_PORT,
      corePort: DEFAULT_PORT,
    },
  };

  constructor() {
    this.logger = new LogService(app);
    this.logger.setLogLevel(resolveLogLevel(undefined, this.appConfig.isDev));
    this.settings = new SettingsManager(app);
    this.processHandler = new SubprocessHandler(this.logger, this.appConfig);
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

  private registerAsDefaultProtocolHandler() {
    // On Linux, registering a URL-scheme handler via xdg-settings can hijack the
    // default text/html association on GNOME with old xdg-utils (issue #12323,
    // xdg-utils#180). Run the registration inside a guard that snapshots and
    // restores the text/html handler if our call corrupts it.
    protectHtmlAssociation(this.logger, () => this.registerProtocolClient());
  }

  private registerProtocolClient(): boolean {
    if (process.defaultApp) {
      // In development we always (re)register so rotki:// deep links point at the
      // current dev binary. On Linux app.isDefaultProtocolClient ignores the
      // path/args, so guarding here would wrongly skip when a production install
      // already claimed the scheme.
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

    // In production, skip re-registering when we are already the default handler
    // so we do not re-run the (destructive on affected Linux setups) xdg-settings
    // call on every launch.
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
      restartSubprocesses: async (options) => {
        this.logger.setLogLevel(resolveLogLevel(options.loglevel, this.appConfig.isDev));
        await this.processHandler.terminateProcesses(true);
        await this.processHandler.startProcesses(options, {
          onProcessError: (message, code) => this.window.setStartupError(message, code),
        });
      },
      terminateSubprocesses: async (update = false) => {
        if (update) {
          this.window.cleanup();
          this.cleanup();
        }
        await this.processHandler.terminateProcesses();
      },
      updateDownloadProgress: progress => this.window.updateProgress(progress),
      getRunningCorePIDs: async () => this.processHandler.checkForBackendProcess(),
      getProtocolRegistrationFailed: () => this.protocolRegistrationFailed,
      openOAuthInWindow: async (url: string) => this.window.openOAuthWindow(url),
      sendIpcMessage: (channel: string, ...args: any[]) => this.window.sendIpcMessage(channel, ...args),
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

  private async quit() {
    this.cleanup();
    this.menu.cleanup();
    this.window.cleanup();
    this.tray.cleanup();
    this.ipc.cleanup();
    try {
      await this.processHandler.terminateProcesses();
    }
    finally {
      // In some cases the app object might be already disposed
      try {
        if (process.platform !== 'win32')
          app.exit();
      }
      catch (error: any) {
        if (error.message !== 'Object has been destroyed')
          console.error(error);
      }
    }
  }
}
