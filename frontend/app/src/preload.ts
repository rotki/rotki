import { contextBridge, ipcRenderer } from 'electron';
import { BackendCode } from '@/electron-main/backend-code';
import { Interop, TrayUpdate } from '@/electron-main/ipc';
import {
  IPC_ABOUT,
  IPC_CHECK_FOR_UPDATES,
  IPC_CLOSE_APP,
  IPC_CONFIG,
  IPC_DARK_MODE,
  IPC_DEBUG_SETTINGS,
  IPC_DOWNLOAD_PROGRESS,
  IPC_DOWNLOAD_UPDATE,
  IPC_GET_DEBUG,
  IPC_INSTALL_UPDATE,
  IPC_METAMASK_IMPORT,
  IPC_OPEN_DIRECTORY,
  IPC_OPEN_PATH,
  IPC_OPEN_URL,
  IPC_PREMIUM_LOGIN,
  IPC_RESTART_BACKEND,
  IPC_SERVER_URL,
  IPC_TRAY_UPDATE,
  IPC_VERSION,
  IPC_WEBSOCKET_URL
} from '@/electron-main/ipc-commands';

function ipcAction<T>(message: string, arg?: any): Promise<T> {
  return new Promise(resolve => {
    ipcRenderer.once(message, (event, args) => {
      resolve(args);
    });
    ipcRenderer.send(message, arg);
  });
}

const isDevelopment = process.env.NODE_ENV !== 'production';

type DebugSettings = { vuex: boolean };
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
  listenForErrors: (
    callback: (backendOutput: string, code: BackendCode) => void
  ) => {
    ipcRenderer.on('failed', (event, error, code) => {
      callback(error, code);
      ipcRenderer.send('ack', 1);
    });
  },
  debugSettings: isDevelopment
    ? (): DebugSettings | undefined => {
        return debugSettings;
      }
    : undefined,
  serverUrl: (): string => ipcRenderer.sendSync(IPC_SERVER_URL),
  websocketUrl: (): string => ipcRenderer.sendSync(IPC_WEBSOCKET_URL),
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
  setDarkMode: (enabled: boolean) => ipcAction(IPC_DARK_MODE, enabled),
  version: () => ipcAction(IPC_VERSION),
  onAbout: (callback: () => void) => {
    ipcRenderer.on(IPC_ABOUT, () => {
      callback();
    });
  },
  openPath: (path: string) => ipcRenderer.send(IPC_OPEN_PATH, path),
  config: (defaults: boolean) => ipcAction(IPC_CONFIG, defaults),
  updateTray: (trayUpdate: TrayUpdate) =>
    ipcRenderer.send(IPC_TRAY_UPDATE, trayUpdate)
} as Interop);
