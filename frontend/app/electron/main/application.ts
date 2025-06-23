import type { AppConfig } from '@electron/main/app-config';
import process from 'node:process';
import { IpcManager } from '@electron/main/ipc-setup';
import { LogService } from '@electron/main/log-service';
import { MenuManager } from '@electron/main/menu';
import { parseToken } from '@electron/main/oauth-utils';
import { DEFAULT_COLIBRI_PORT, DEFAULT_PORT } from '@electron/main/port-utils';
import { SettingsManager } from '@electron/main/settings-manager';
import { SubprocessHandler } from '@electron/main/subprocess-handler';
import { TrayManager } from '@electron/main/tray-manager';
import { WindowManager } from '@electron/main/window-manager';
import { LogLevel } from '@shared/log-level';
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
    // Register the app as the default handler for rotki:// protocol
    if (process.defaultApp) {
      // In development
      if (process.argv.length >= 2) {
        this.logger.info(`Registering ${process.execPath} ${process.argv[1]} as the default handler for rotki:// protocol`);
        const registrationSuccess = app.setAsDefaultProtocolClient('rotki', process.execPath, [process.argv[1]]);
        if (!registrationSuccess) {
          this.protocolRegistrationFailed = true;
          this.logger.warn(`Failed to register ${process.execPath} ${process.argv[1]} as the default handler for rotki:// protocol`);
        }
      }
    }
    else {
      // In production
      this.logger.info(`Registering the app as the default handler for rotki:// protocol`);
      const registrationSuccess = app.setAsDefaultProtocolClient('rotki');
      if (!registrationSuccess) {
        this.protocolRegistrationFailed = true;
        this.logger.warn(`Failed to register the app as the default handler for rotki:// protocol`);
      }
    }
  }

  private async initialize() {
    this.registerAsDefaultProtocolHandler();

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
        this.logger.setLogLevel(options.loglevel ?? this.appConfig.isDev ? LogLevel.DEBUG : LogLevel.INFO);
        await this.processHandler.terminateProcesses(true);
        await this.processHandler.startProcesses(options, {
          onProcessError: (message, code) => this.window.notify(message, code),
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
