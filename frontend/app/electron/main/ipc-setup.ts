import type { AppConfig } from '@electron/main/app-config';
import type { LogService } from '@electron/main/log-service';
import type { SettingsManager } from '@electron/main/settings-manager';
import type { BackendOptions, Credentials, SystemVersion, TrayUpdate } from '@shared/ipc';
import type { ProgressInfo } from 'electron-builder';
import process from 'node:process';
import { IpcCommands } from '@electron/ipc-commands';
import { loadConfig } from '@electron/main/config';
import { HttpServer } from '@electron/main/http';
import { PasswordManager } from '@electron/main/password-manager';
import { selectPort } from '@electron/main/port-utils';
import { assert, type DebugSettings } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { dialog, ipcMain, nativeTheme, shell } from 'electron';
import electronUpdater from 'electron-updater';

const { autoUpdater } = electronUpdater;

interface Callbacks {
  quit: () => Promise<void>;
  updateTray: (trayUpdate: TrayUpdate) => void;
  updatePremiumMenu: (isPremium: boolean) => void;
  restartSubprocesses: (options: Partial<BackendOptions>) => Promise<void>;
  terminateSubprocesses: (update?: boolean) => Promise<void>;
  getRunningCorePIDs: () => Promise<number[]>;
  updateDownloadProgress: (progress: number) => void;
}

export class IpcManager {
  private readonly passwordManager = new PasswordManager();
  private readonly httpServer: HttpServer;
  private walletImportTimeout: NodeJS.Timeout | undefined;

  private firstStart = true;
  private restarting = false;
  private callbacks: Callbacks | null = null;

  private static readonly updateTimeout = 5000;

  private readonly version: SystemVersion = {
    os: process.platform,
    arch: process.arch,
    osVersion: process.getSystemVersion(),
    electron: process.versions.electron,
  };

  private get requireCallbacks(): Callbacks {
    const callbacks = this.callbacks;
    assert(callbacks);
    return callbacks;
  }

  constructor(
    private readonly logger: LogService,
    private readonly settings: SettingsManager,
    private readonly config: AppConfig,
  ) {
    this.httpServer = new HttpServer(logger);
  }

  initialize(callbacks: Callbacks) {
    this.callbacks = callbacks;
    this.logger.log('Registering IPC handlers');
    ipcMain.on(IpcCommands.SYNC_GET_DEBUG, (event) => {
      event.returnValue = { persistStore: this.settings.appSettings.persistStore ?? false } satisfies DebugSettings;
    });

    ipcMain.on(IpcCommands.SYNC_API_URL, (event) => {
      event.returnValue = this.config.urls;
    });

    ipcMain.on(IpcCommands.PREMIUM_LOGIN, (_event, showPremium) => {
      callbacks.updatePremiumMenu(showPremium);
    });

    ipcMain.handle(IpcCommands.INVOKE_CLOSE_APP, callbacks.quit);
    ipcMain.handle(IpcCommands.INVOKE_OPEN_URL, this.openUrl);
    ipcMain.handle(IpcCommands.INVOKE_OPEN_DIRECTORY, this.openDirectory);
    ipcMain.handle(IpcCommands.INVOKE_OPEN_PATH, this.openPath);

    ipcMain.handle(IpcCommands.INVOKE_CONFIG, this.getConfig);
    ipcMain.handle(IpcCommands.INVOKE_WALLET_IMPORT, this.importFromWallet);
    ipcMain.handle(IpcCommands.OPEN_WALLET_CONNECT_BRIDGE, this.openWalletConnectBridge);
    ipcMain.handle(IpcCommands.INVOKE_VERSION, () => this.version);
    ipcMain.handle(IpcCommands.INVOKE_IS_MAC, () => this.version.os === 'darwin');

    ipcMain.on(IpcCommands.LOG_TO_FILE, (_, message: string) => this.logger.log(message));

    ipcMain.handle(IpcCommands.INVOKE_THEME, (event, selectedTheme: number) => {
      const themeSource = ['dark', 'system', 'light'] as const;
      nativeTheme.themeSource = themeSource[selectedTheme];
      return nativeTheme.shouldUseDarkColors;
    });

    ipcMain.handle(IpcCommands.INVOKE_SUBPROCESS_START, this.restartBackend);

    ipcMain.on(IpcCommands.TRAY_UPDATE, (_event, trayUpdate: TrayUpdate) => {
      callbacks.updateTray(trayUpdate);
    });
    this.setupUpdaterInterop();

    ipcMain.handle(
      IpcCommands.INVOKE_STORE_PASSWORD,
      async (_, credentials: Credentials) => this.passwordManager.storePassword(credentials),
    );
    ipcMain.handle(
      IpcCommands.INVOKE_GET_PASSWORD,
      async (_, username: string) => this.passwordManager.retrievePassword(username),
    );
    ipcMain.handle(
      IpcCommands.INVOKE_CLEAR_PASSWORD,
      async () => this.passwordManager.clearPasswords(),
    );
  }

  private readonly select = async (
    title: string,
    prop: 'openFile' | 'openDirectory',
    defaultPath?: string,
  ): Promise<string | undefined> => {
    const value = await dialog.showOpenDialog({
      title,
      defaultPath,
      properties: [prop],
    });

    if (value.canceled)
      return undefined;

    return value.filePaths?.[0];
  };

  private readonly openUrl = async (_event: Electron.IpcMainInvokeEvent, url: string): Promise<void> => {
    if (!url.startsWith('https://')) {
      console.error(`Error: Requested to open untrusted URL: ${url} `);
      return;
    }
    await shell.openExternal(url);
  };

  private readonly openDirectory = async (_event: Electron.IpcMainInvokeEvent, title: string, defaultPath?: string): Promise<string | undefined> => {
    try {
      return await this.select(title, 'openDirectory', defaultPath);
    }
    catch (error: any) {
      console.error(error);
      return undefined;
    }
  };

  private readonly openPath = (_event: Electron.IpcMainInvokeEvent, path: string): void => {
    shell.openPath(path).catch(error => this.logger.log(error));
  };

  private readonly getConfig = async (_event: Electron.IpcMainInvokeEvent, defaultConfig: boolean): Promise<Partial<BackendOptions>> => {
    if (defaultConfig) {
      return { logDirectory: this.logger.defaultLogDirectory };
    }
    else {
      return loadConfig();
    }
  };

  private readonly importFromWallet = async (): Promise<{ error: string } | { addresses: string[] }> => {
    try {
      const portNumber = await selectPort(40000);
      return await new Promise((resolve) => {
        const port = this.httpServer.start(
          addresses => resolve({ addresses }),
          portNumber,
        );

        shell.openExternal(`http://localhost:${port}`).catch((error) => {
          resolve({ error: error.message });
        });

        if (this.walletImportTimeout)
          clearTimeout(this.walletImportTimeout);

        this.walletImportTimeout = setTimeout(() => {
          this.httpServer.stop();
          resolve({ error: 'waiting timeout' });
        }, 120000);
      });
    }
    catch (error: any) {
      return { error: error.message };
    }
  };

  private walletConnectBridgePort: number | undefined = undefined;

  private readonly openWalletConnectBridge = async (): Promise<void> => {
    try {
      // If server is already running, just open the existing URL
      if (this.walletConnectBridgePort) {
        this.logger.log(`Wallet Connect Bridge already running at http://localhost:${this.walletConnectBridgePort}`);
        await shell.openExternal(`http://localhost:${this.walletConnectBridgePort}/#/wallet-bridge`);
        return;
      }

      const portNumber = await selectPort(40010);
      this.walletConnectBridgePort = portNumber; // Store the port

      this.httpServer.startWalletConnectBridgeServer(portNumber);

      // Open the Wallet Connect Bridge in Electron (same URL in dev/prod)
      await shell.openExternal(`http://localhost:${portNumber}/#/wallet-bridge`);
    }
    catch (error: any) {
      this.logger.log(`Error opening Wallet Connect Bridge: ${error}`);
    }
  };

  private readonly restartBackend = async (event: Electron.IpcMainInvokeEvent, options: Partial<BackendOptions>): Promise<boolean> => {
    this.logger.log(`Restarting backend with options: ${JSON.stringify(options)}`);
    if (this.firstStart) {
      this.firstStart = false;
      const pids = await this.requireCallbacks.getRunningCorePIDs();
      if (pids.length > 0) {
        event.sender.send(IpcCommands.BACKEND_PROCESS_DETECTED, pids);
        this.logger.log(`Detected existing backend process: ${pids.join(', ')}`);
      }
      else {
        this.logger.log('No existing backend process detected');
      }
    }

    let success = false;

    if (!this.restarting) {
      this.restarting = true;
      try {
        this.logger.log('Starting backend process');
        await this.requireCallbacks.restartSubprocesses(options);
        success = true;
      }
      catch (error: any) {
        this.logger.log(error);
      }
      finally {
        this.restarting = false;
      }
    }

    return success;
  };

  private readonly installUpdate = async (): Promise<Error | boolean> => {
    const quit = new Promise<void>((resolve, reject) => setTimeout(() => {
      startPromise((async () => {
        try {
          await this.quitAndInstallUpdates();
          resolve();
        }
        catch (error: any) {
          this.logger.log(error);
          reject(error instanceof Error ? error : new Error(error));
        }
      })());
    }, IpcManager.updateTimeout));

    try {
      await quit;
      return true;
    }
    catch (error: any) {
      this.logger.log(error);
      return error;
    }
  };

  private async quitAndInstallUpdates() {
    await this.requireCallbacks.terminateSubprocesses(true);
    autoUpdater.quitAndInstall();
  }

  private readonly downloadUpdate = async (event: Electron.IpcMainInvokeEvent): Promise<boolean> => {
    const progress = (progress: ProgressInfo) => {
      event.sender.send(IpcCommands.DOWNLOAD_PROGRESS, progress.percent);
      this.requireCallbacks.updateDownloadProgress(progress.percent);
    };

    return new Promise<boolean>((resolve) => {
      autoUpdater.on('download-progress', progress);
      autoUpdater.downloadUpdate()
        .then(() => resolve(true))
        .catch((error) => {
          this.logger.log(error);
          resolve(false);
        })
        .finally(() => {
          autoUpdater.removeListener('download-progress', progress);
        });
    });
  };

  private readonly checkForUpdates = async (): Promise<boolean> => {
    if (this.config.isDev) {
      console.warn('Running in development skipping auto-updater check');
      return false;
    }

    return new Promise<boolean>((resolve) => {
      autoUpdater.once('update-available', () => resolve(true));
      autoUpdater.once('update-not-available', () => resolve(false));
      autoUpdater.once('error', (error: Error) => {
        console.error(error);
        this.logger.log(error);
        resolve(false);
      });

      autoUpdater.checkForUpdates().catch((error: any) => {
        console.error(error);
        this.logger.log(error);
        resolve(false);
      });
    });
  };

  private setupUpdaterInterop() {
    autoUpdater.autoDownload = false;
    autoUpdater.logger = {
      error: (message?: any) => this.logger.log(`(error): ${message}`),
      info: (message?: any) => this.logger.log(`(info): ${message}`),
      debug: (message: string) => this.logger.log(`(debug): ${message}`),
      warn: (message?: any) => this.logger.log(`(warn): ${message}`),
    };
    ipcMain.handle(IpcCommands.INVOKE_UPDATE_CHECK, this.checkForUpdates);
    ipcMain.handle(IpcCommands.INVOKE_DOWNLOAD_UPDATE, this.downloadUpdate);
    ipcMain.handle(IpcCommands.INVOKE_INSTALL_UPDATE, this.installUpdate);
  }
}
