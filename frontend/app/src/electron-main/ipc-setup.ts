import process from 'node:process';
import { Buffer } from 'node:buffer';
import {
  type BrowserWindow,
  Menu,
  dialog,
  ipcMain,
  nativeTheme,
  safeStorage,
  shell,
} from 'electron';
import Store from 'electron-store';
import { autoUpdater } from 'electron-updater';
import { loadConfig } from '@/electron-main/config';
import { startHttp, stopHttp } from '@/electron-main/http';
import {
  IPC_BACKEND_PROCESS_DETECTED,
  IPC_CHECK_FOR_UPDATES,
  IPC_CLEAR_PASSWORD,
  IPC_CLOSE_APP,
  IPC_CONFIG,
  IPC_DOWNLOAD_PROGRESS,
  IPC_DOWNLOAD_UPDATE,
  IPC_GET_DEBUG,
  IPC_GET_PASSWORD,
  IPC_INSTALL_UPDATE,
  IPC_IS_MAC,
  IPC_LOG_TO_FILE,
  IPC_METAMASK_IMPORT,
  IPC_OPEN_DIRECTORY,
  IPC_OPEN_PATH,
  IPC_OPEN_URL,
  IPC_PREMIUM_LOGIN,
  IPC_RESTART_BACKEND,
  IPC_SERVER_URL,
  IPC_STORE_PASSWORD,
  IPC_THEME,
  IPC_TRAY_UPDATE,
  IPC_VERSION,
} from '@/electron-main/ipc-commands';
import {
  type MenuActions,
  debugSettings,
  getUserMenu,
} from '@/electron-main/menu';
import { selectPort } from '@/electron-main/port-utils';
import { checkIfDevelopment } from '@/utils/env-utils';
import { startPromise } from '@/utils';
import type { TrayManager } from '@/electron-main/tray-manager';
import type {
  BackendOptions,
  SystemVersion,
  TrayUpdate,
} from '@/electron-main/ipc';
import type { ProgressInfo } from 'electron-builder';
import type { SubprocessHandler } from '@/subprocess-handler';

const isDevelopment = checkIfDevelopment();

type WindowProvider = () => BrowserWindow;

async function select(
  title: string,
  prop: 'openFile' | 'openDirectory',
  defaultPath?: string,
): Promise<string | undefined> {
  const value = await dialog.showOpenDialog({
    title,
    defaultPath,
    properties: [prop],
  });

  if (value.canceled)
    return undefined;

  return value.filePaths?.[0];
}

function setupMetamaskImport() {
  let importTimeout: any;

  async function importFromMetamask(event: Electron.IpcMainEvent) {
    try {
      const port = startHttp(
        addresses => event.sender.send(IPC_METAMASK_IMPORT, { addresses }),
        await selectPort(40000),
      );
      await shell.openExternal(`http://localhost:${port}`);
      if (importTimeout)
        clearTimeout(importTimeout);

      importTimeout = setTimeout(() => {
        stopHttp();
        event.sender.send(IPC_METAMASK_IMPORT, { error: 'waiting timeout' });
      }, 120000);
    }
    catch (error: any) {
      event.sender.send(IPC_METAMASK_IMPORT, { error: error.message });
    }
  }

  ipcMain.on(IPC_METAMASK_IMPORT, (event, _args) => startPromise(importFromMetamask(event)));
}

let firstStart = true;
let restarting = false;

function setupBackendRestart(
  getWindow: WindowProvider,
  pyHandler: SubprocessHandler,
) {
  async function restartBackend(event: Electron.IpcMainEvent, options: Partial<BackendOptions>) {
    if (firstStart) {
      firstStart = false;
      const pids = await pyHandler.checkForBackendProcess();
      if (pids.length > 0)
        event.sender.send(IPC_BACKEND_PROCESS_DETECTED, pids);
    }

    let success = false;

    if (!restarting) {
      restarting = true;
      try {
        const win = getWindow();
        await pyHandler.exitPyProc(true);
        await pyHandler.createPyProc(win, options);
        success = true;
      }
      catch (error: any) {
        console.error(error);
      }
      finally {
        restarting = false;
      }
    }

    event.sender.send(IPC_RESTART_BACKEND, success);
  }

  ipcMain.on(IPC_RESTART_BACKEND, (event, options: Partial<BackendOptions>) => {
    startPromise(restartBackend(event, options));
  });
}

function setupVersionInfo() {
  const version: SystemVersion = {
    os: process.platform,
    arch: process.arch,
    osVersion: process.getSystemVersion(),
    electron: process.versions.electron,
  };

  ipcMain.on(IPC_VERSION, (event) => {
    event.sender.send(IPC_VERSION, version);
  });

  ipcMain.on(IPC_IS_MAC, (event) => {
    const isMac = (version)?.os === 'darwin';
    event.sender.send(IPC_IS_MAC, isMac);
  });
}

function setupSelectedTheme() {
  ipcMain.on(IPC_THEME, (event, selectedTheme: number) => {
    const themeSource = ['dark', 'system', 'light'] as const;
    nativeTheme.themeSource = themeSource[selectedTheme];
    event.sender.send(IPC_THEME, nativeTheme.shouldUseDarkColors);
  });
}

function setupTrayInterop(trayManager: TrayManager) {
  ipcMain.on(IPC_TRAY_UPDATE, (_event, trayUpdate: TrayUpdate) => {
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
    if (buffer)
      return safeStorage.decryptString(Buffer.from(buffer, encoding));

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
    },
  );

  ipcMain.on(IPC_GET_PASSWORD, (event, username: string) => {
    let password = '';
    if (getEncryptionAvailability())
      password = getPassword(username);

    event.sender.send(IPC_GET_PASSWORD, password);
  });

  ipcMain.on(IPC_CLEAR_PASSWORD, (event) => {
    if (getEncryptionAvailability())
      clearPassword();

    event.sender.send(IPC_CLEAR_PASSWORD);
  });
}

export function ipcSetup(
  pyHandler: SubprocessHandler,
  getWindow: WindowProvider,
  closeApp: () => Promise<void>,
  tray: TrayManager,
  menuActions: MenuActions,
  ensureSafeUpdateRestart: () => void,
) {
  ipcMain.on(IPC_GET_DEBUG, (event) => {
    event.returnValue = debugSettings;
  });

  ipcMain.on(IPC_SERVER_URL, (event) => {
    event.returnValue = pyHandler.serverUrl;
  });

  ipcMain.on(IPC_PREMIUM_LOGIN, (_event, args) => {
    Menu.setApplicationMenu(
      Menu.buildFromTemplate(getUserMenu(!args, menuActions)),
    );
  });

  ipcMain.on(IPC_CLOSE_APP, () => startPromise(closeApp()));

  ipcMain.on(IPC_OPEN_URL, (_event, args) => {
    if (!args.startsWith('https://')) {
      console.error(`Error: Requested to open untrusted URL: ${args} `);
      return;
    }
    startPromise(shell.openExternal(args));
  });

  ipcMain.on(IPC_OPEN_DIRECTORY, (event, title: string, defaultPath?: string) => {
    select(title, 'openDirectory', defaultPath).then((directory) => {
      event.sender.send(IPC_OPEN_DIRECTORY, directory);
    }).catch(error => console.error(error));
  });
  ipcMain.on(IPC_OPEN_PATH, (_event, path) => {
    startPromise(shell.openPath(path));
  });
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
  setupUpdaterInterop(pyHandler, getWindow, ensureSafeUpdateRestart);
  setupSelectedTheme();
  setupBackendRestart(getWindow, pyHandler);
  setupTrayInterop(tray);
  setupPasswordStorage();
}

function setupInstallUpdate(
  pyHandler: SubprocessHandler,
  ensureSafeUpdateRestart: () => void,
) {
  async function installUpdate(event: Electron.IpcMainEvent) {
    const quit = new Promise<void>((resolve, reject) => {
      const quitAndInstall = async () => {
        try {
          ensureSafeUpdateRestart();
          await pyHandler.exitPyProc();
          autoUpdater.quitAndInstall();
          resolve();
        }
        catch (error: any) {
          pyHandler.logToFile(error);
          reject(error);
        }
      };
      return setTimeout(() => {
        startPromise(quitAndInstall());
      }, 5000);
    });
    try {
      await quit;
      event.sender.send(IPC_INSTALL_UPDATE, true);
    }
    catch (error: any) {
      pyHandler.logToFile(error);
      event.sender.send(IPC_INSTALL_UPDATE, error);
    }
  }

  ipcMain.on(IPC_INSTALL_UPDATE, event => startPromise(installUpdate(event)));
}

function setupDownloadUpdate(
  getWindow: WindowProvider,
  pyHandler: SubprocessHandler,
) {
  async function downloadUpdate(event: Electron.IpcMainEvent) {
    const window = getWindow();
    const progress = (progress: ProgressInfo) => {
      event.sender.send(IPC_DOWNLOAD_PROGRESS, progress.percent);
      window.setProgressBar(progress.percent);
    };
    autoUpdater.on('download-progress', progress);
    try {
      await autoUpdater.downloadUpdate();
      event.sender.send(IPC_DOWNLOAD_UPDATE, true);
    }
    catch (error: any) {
      pyHandler.logToFile(error);
      event.sender.send(IPC_DOWNLOAD_UPDATE, false);
    }
    finally {
      autoUpdater.off('download-progress', progress);
    }
  }

  ipcMain.on(IPC_DOWNLOAD_UPDATE, event => startPromise(downloadUpdate(event)));
}

function setupCheckForUpdates(pyHandler: SubprocessHandler) {
  async function checkForUpdates(event: Electron.IpcMainEvent) {
    if (isDevelopment) {
      console.warn('Running in development skipping auto-updater check');
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
    }
    catch (error: any) {
      console.error(error);
      pyHandler.logToFile(error);
      event.sender.send(IPC_CHECK_FOR_UPDATES, false);
    }
  }

  ipcMain.on(IPC_CHECK_FOR_UPDATES, event => startPromise(checkForUpdates(event)));
}

function setupUpdaterInterop(
  pyHandler: SubprocessHandler,
  getWindow: WindowProvider,
  ensureSafeUpdateRestart: () => void,
) {
  autoUpdater.autoDownload = false;
  autoUpdater.logger = {
    error: (message?: any) => pyHandler.logToFile(`(error): ${message}`),
    info: (message?: any) => pyHandler.logToFile(`(info): ${message}`),
    debug: (message: string) => pyHandler.logToFile(`(debug): ${message}`),
    warn: (message?: any) => pyHandler.logToFile(`(warn): ${message}`),
  };
  setupCheckForUpdates(pyHandler);
  setupDownloadUpdate(getWindow, pyHandler);
  setupInstallUpdate(pyHandler, ensureSafeUpdateRestart);
}
