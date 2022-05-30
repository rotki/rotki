import {
  BrowserWindow,
  dialog,
  ipcMain,
  Menu,
  nativeTheme,
  shell,
  safeStorage
} from 'electron';
import { ProgressInfo } from 'electron-builder';
import Store from 'electron-store';
import { autoUpdater } from 'electron-updater';
import { loadConfig } from '@/electron-main/config';
import { startHttp, stopHttp } from '@/electron-main/http';
import { BackendOptions, SystemVersion, TrayUpdate } from '@/electron-main/ipc';
import {
  IPC_CHECK_FOR_UPDATES,
  IPC_CLOSE_APP,
  IPC_CONFIG,
  IPC_DARK_MODE,
  IPC_CLEAR_PASSWORD,
  IPC_DOWNLOAD_PROGRESS,
  IPC_DOWNLOAD_UPDATE,
  IPC_GET_DEBUG,
  IPC_GET_PASSWORD,
  IPC_INSTALL_UPDATE,
  IPC_LOG_TO_FILE,
  IPC_METAMASK_IMPORT,
  IPC_OPEN_DIRECTORY,
  IPC_OPEN_PATH,
  IPC_OPEN_URL,
  IPC_PREMIUM_LOGIN,
  IPC_RESTART_BACKEND,
  IPC_SERVER_URL,
  IPC_STORE_PASSWORD,
  IPC_TRAY_UPDATE,
  IPC_VERSION,
  IPC_WEBSOCKET_URL
} from '@/electron-main/ipc-commands';
import { debugSettings, getUserMenu, MenuActions } from '@/electron-main/menu';
import { selectPort } from '@/electron-main/port-utils';
import { TrayManager } from '@/electron-main/tray-manager';
import PyHandler from '@/py-handler';

const isDevelopment = process.env.NODE_ENV !== 'production';

type WindowProvider = () => BrowserWindow;

async function select(
  title: string,
  prop: 'openFile' | 'openDirectory',
  defaultPath?: string
): Promise<string | undefined> {
  const value = await dialog.showOpenDialog({
    title,
    defaultPath,
    properties: [prop]
  });

  if (value.canceled) {
    return undefined;
  }
  return value.filePaths?.[0];
}

function setupMetamaskImport() {
  let importTimeout: any;
  ipcMain.on(IPC_METAMASK_IMPORT, async (event, _args) => {
    try {
      const port = startHttp(
        addresses => event.sender.send(IPC_METAMASK_IMPORT, { addresses }),
        await selectPort(40000)
      );
      await shell.openExternal(`http://localhost:${port}`);
      if (importTimeout) {
        clearTimeout(importTimeout);
      }
      importTimeout = setTimeout(() => {
        stopHttp();
        event.sender.send(IPC_METAMASK_IMPORT, { error: 'waiting timeout' });
      }, 120000);
    } catch (e: any) {
      event.sender.send(IPC_METAMASK_IMPORT, { error: e.message });
    }
  });
}

function setupBackendRestart(getWindow: WindowProvider, pyHandler: PyHandler) {
  ipcMain.on(
    IPC_RESTART_BACKEND,
    async (event, options: Partial<BackendOptions>) => {
      let success = false;
      try {
        const win = getWindow();
        await pyHandler.exitPyProc(true);
        await pyHandler.createPyProc(win, options);
        success = true;
      } catch (e: any) {
        console.error(e);
      }

      event.sender.send(IPC_RESTART_BACKEND, success);
    }
  );
}

function setupVersionInfo() {
  ipcMain.on(IPC_VERSION, event => {
    const version: SystemVersion = {
      os: process.platform,
      arch: process.arch,
      osVersion: process.getSystemVersion(),
      electron: process.versions.electron
    };
    event.sender.send(IPC_VERSION, version);
  });
}

function setupDarkModeSupport() {
  ipcMain.on(IPC_DARK_MODE, async (event, enabled) => {
    if (enabled) {
      nativeTheme.themeSource = 'dark';
    } else {
      nativeTheme.themeSource = 'light';
    }
    event.sender.send(IPC_DARK_MODE, nativeTheme.shouldUseDarkColors);
  });
}

function setupTrayInterop(trayManager: TrayManager) {
  ipcMain.on(IPC_TRAY_UPDATE, async (event, trayUpdate: TrayUpdate) => {
    trayManager.update(trayUpdate);
  });
}

function setupPasswordStorage() {
  const store = new Store<Record<string, string>>();

  const encoding = 'latin1';

  const getEncryptionAvailability = (): boolean =>
    safeStorage.isEncryptionAvailable();

  const setPassword = (key: string, password: string) => {
    const buffer = safeStorage.encryptString(password);
    store.set(key, buffer.toString(encoding));
  };

  const clearPassword = () => {
    store.clear();
  };

  const getPassword = (key: string) => {
    const buffer = store.store?.[key];
    if (buffer) {
      return safeStorage.decryptString(Buffer.from(buffer, encoding));
    }

    return '';
  };

  ipcMain.on(
    IPC_STORE_PASSWORD,
    (event, { username, password }: { username: string; password: string }) => {
      let success = false;
      if (getEncryptionAvailability()) {
        setPassword(username, password);
        success = true;
      }
      event.sender.send(IPC_STORE_PASSWORD, success);
    }
  );

  ipcMain.on(IPC_GET_PASSWORD, (event, username: string) => {
    let password = '';
    if (getEncryptionAvailability()) {
      password = getPassword(username);
    }
    event.sender.send(IPC_GET_PASSWORD, password);
  });

  ipcMain.on(IPC_CLEAR_PASSWORD, () => {
    if (getEncryptionAvailability()) {
      clearPassword();
    }
  });
}

export function ipcSetup(
  pyHandler: PyHandler,
  getWindow: WindowProvider,
  closeApp: () => Promise<void>,
  tray: TrayManager,
  menuActions: MenuActions
) {
  ipcMain.on(IPC_GET_DEBUG, event => {
    event.returnValue = debugSettings;
  });

  ipcMain.on(IPC_SERVER_URL, event => {
    event.returnValue = pyHandler.serverUrl;
  });

  ipcMain.on(IPC_WEBSOCKET_URL, event => {
    event.returnValue = pyHandler.websocketUrl;
  });

  ipcMain.on(IPC_PREMIUM_LOGIN, (event, args) => {
    Menu.setApplicationMenu(
      Menu.buildFromTemplate(getUserMenu(!args, menuActions))
    );
  });

  ipcMain.on(IPC_CLOSE_APP, async () => await closeApp());

  ipcMain.on(IPC_OPEN_URL, (event, args) => {
    if (!args.startsWith('https://')) {
      console.error(`Error: Requested to open untrusted URL: ${args} `);
      return;
    }
    shell.openExternal(args);
  });

  ipcMain.on(
    IPC_OPEN_DIRECTORY,
    async (event, title: string, defaultPath?: string) => {
      const directory = await select(title, 'openDirectory', defaultPath);
      event.sender.send(IPC_OPEN_DIRECTORY, directory);
    }
  );
  ipcMain.on(IPC_OPEN_PATH, (event, path) => shell.openPath(path));
  ipcMain.on(IPC_CONFIG, (event, defaults: boolean) => {
    const options: Partial<BackendOptions> = defaults
      ? { logDirectory: pyHandler.defaultLogDirectory }
      : loadConfig();
    event.sender.send(IPC_CONFIG, options);
  });

  ipcMain.on(IPC_LOG_TO_FILE, (_, message: string) => {
    pyHandler.logToFile(message);
  });

  setupMetamaskImport();
  setupVersionInfo();
  setupUpdaterInterop(pyHandler, getWindow);
  setupDarkModeSupport();
  setupBackendRestart(getWindow, pyHandler);
  setupTrayInterop(tray);
  setupPasswordStorage();
}

function setupInstallUpdate(pyHandler: PyHandler) {
  ipcMain.on(IPC_INSTALL_UPDATE, async event => {
    const quit = new Promise<void>((resolve, reject) => {
      const quitAndInstall = () => {
        try {
          autoUpdater.quitAndInstall();
          resolve();
        } catch (e: any) {
          pyHandler.logToFile(e);
          reject(e);
        }
      };
      return setTimeout(quitAndInstall, 5000);
    });
    try {
      await quit;
      event.sender.send(IPC_INSTALL_UPDATE, true);
    } catch (e: any) {
      pyHandler.logToFile(e);
      event.sender.send(IPC_INSTALL_UPDATE, e);
    }
  });
}

function setupDownloadUpdate(getWindow: WindowProvider, pyHandler: PyHandler) {
  ipcMain.on(IPC_DOWNLOAD_UPDATE, async event => {
    const window = getWindow();
    const progress = (progress: ProgressInfo) => {
      event.sender.send(IPC_DOWNLOAD_PROGRESS, progress.percent);
      window.setProgressBar(progress.percent);
    };
    autoUpdater.on('download-progress', progress);
    try {
      await autoUpdater.downloadUpdate();
      event.sender.send(IPC_DOWNLOAD_UPDATE, true);
    } catch (e: any) {
      pyHandler.logToFile(e);
      event.sender.send(IPC_DOWNLOAD_UPDATE, false);
    } finally {
      autoUpdater.off('download-progress', progress);
    }
  });
}

function setupCheckForUpdates(pyHandler: PyHandler) {
  ipcMain.on(IPC_CHECK_FOR_UPDATES, async event => {
    if (isDevelopment) {
      console.log('Running in development skipping auto-updater check');
      return;
    }
    autoUpdater.once('update-available', () => {
      event.sender.send(IPC_CHECK_FOR_UPDATES, true);
    });
    autoUpdater.once('update-not-available', () => {
      event.sender.send(IPC_CHECK_FOR_UPDATES, false);
    });
    try {
      await autoUpdater.checkForUpdates();
    } catch (e: any) {
      console.error(e);
      pyHandler.logToFile(e);
      event.sender.send(IPC_CHECK_FOR_UPDATES, false);
    }
  });
}

function setupUpdaterInterop(pyHandler: PyHandler, getWindow: WindowProvider) {
  autoUpdater.autoDownload = false;
  autoUpdater.logger = {
    error: (message?: any) => pyHandler.logToFile(`(error): ${message}`),
    info: (message?: any) => pyHandler.logToFile(`(info): ${message}`),
    debug: (message: string) => pyHandler.logToFile(`(debug): ${message}`),
    warn: (message?: any) => pyHandler.logToFile(`(warn): ${message}`)
  };
  setupCheckForUpdates(pyHandler);
  setupDownloadUpdate(getWindow, pyHandler);
  setupInstallUpdate(pyHandler);
}
