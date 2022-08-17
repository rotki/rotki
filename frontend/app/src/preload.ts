import { contextBridge, ipcRenderer } from 'electron';
import { Interop, Listeners, TrayUpdate } from '@/electron-main/ipc';
import {
  IPC_ABOUT,
  IPC_BACKEND_PROCESS_DETECTED,
  IPC_CHECK_FOR_UPDATES,
  IPC_CLEAR_PASSWORD,
  IPC_CLOSE_APP,
  IPC_CONFIG,
  IPC_DEBUG_SETTINGS,
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
  IPC_REQUEST_RESTART,
  IPC_RESTART_BACKEND,
  IPC_SERVER_URL,
  IPC_STORE_PASSWORD,
  IPC_THEME,
  IPC_TRAY_UPDATE,
  IPC_VERSION
} from '@/electron-main/ipc-commands';
import { checkIfDevelopment } from '@/utils/env-utils';

function ipcAction<T>(message: string, arg?: any): Promise<T> {
  return new Promise(resolve => {
    ipcRenderer.once(message, (event, args) => {
      resolve(args);
    });
    ipcRenderer.send(message, arg);
  });
}

const isDevelopment = checkIfDevelopment();

type DebugSettings = { persistStore: boolean };
let debugSettings: DebugSettings | undefined = isDevelopment
  ? ipcRenderer.sendSync(IPC_GET_DEBUG)
  : undefined;

if (isDevelopment) {
  ipcRenderer.on(IPC_DEBUG_SETTINGS, (event, args) => {
    debugSettings = args;
  });
}

contextBridge.exposeInMainWorld('interop', {
  openUrl: (url: string) => ipcRenderer.send(IPC_OPEN_URL, url),
  closeApp: () => ipcRenderer.send(IPC_CLOSE_APP),
  openDirectory: (title: string) => ipcAction(IPC_OPEN_DIRECTORY, title),
  premiumUserLoggedIn: (premiumUser: boolean) =>
    ipcRenderer.send(IPC_PREMIUM_LOGIN, premiumUser),
  setListeners(listeners: Listeners): void {
    ipcRenderer.on('failed', (event, error, code) => {
      listeners.onError(error, code);
      ipcRenderer.send('ack', 1);
    });

    ipcRenderer.on(IPC_REQUEST_RESTART, () => {
      listeners.onRestart();
    });

    ipcRenderer.on(IPC_ABOUT, () => {
      listeners.onAbout();
    });

    ipcRenderer.on(IPC_BACKEND_PROCESS_DETECTED, (_event, pids) => {
      listeners.onProcessDetected(pids);
    });
  },
  debugSettings: isDevelopment
    ? (): DebugSettings | undefined => {
        return debugSettings;
      }
    : undefined,
  serverUrl: (): string => ipcRenderer.sendSync(IPC_SERVER_URL),
  metamaskImport: () => ipcAction(IPC_METAMASK_IMPORT),
  restartBackend: options => ipcAction(IPC_RESTART_BACKEND, options),
  checkForUpdates: () => ipcAction(IPC_CHECK_FOR_UPDATES),
  downloadUpdate: progress => {
    ipcRenderer.on(IPC_DOWNLOAD_PROGRESS, (event, args) => {
      progress(args);
    });
    return ipcAction(IPC_DOWNLOAD_UPDATE);
  },
  installUpdate: () => ipcAction(IPC_INSTALL_UPDATE),
  setSelectedTheme: selectedTheme => ipcAction(IPC_THEME, selectedTheme),
  version: () => ipcAction(IPC_VERSION),
  isMac: () => ipcAction(IPC_IS_MAC),
  openPath: (path: string) => ipcRenderer.send(IPC_OPEN_PATH, path),
  config: (defaults: boolean) => ipcAction(IPC_CONFIG, defaults),
  updateTray: (trayUpdate: TrayUpdate) =>
    ipcRenderer.send(IPC_TRAY_UPDATE, trayUpdate),
  logToFile(message: string) {
    ipcRenderer.send(IPC_LOG_TO_FILE, message);
  },
  storePassword: (username: string, password: string) =>
    ipcAction(IPC_STORE_PASSWORD, { username, password }),
  getPassword: (username: string) => ipcAction(IPC_GET_PASSWORD, username),
  clearPassword: () => ipcAction(IPC_CLEAR_PASSWORD)
} as Interop);
