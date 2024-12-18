import { contextBridge, ipcRenderer } from 'electron';
import { IpcCommands } from '@electron/ipc-commands';
import { checkIfDevelopment } from '@shared/utils';
import type { Interop, Listeners, TrayUpdate } from '@shared/ipc';

async function ipcAction<T>(message: string, arg?: any): Promise<T> {
  return new Promise((resolve) => {
    ipcRenderer.once(message, (event, args) => {
      resolve(args);
    });
    ipcRenderer.send(message, arg);
  });
}

const isDevelopment = checkIfDevelopment();

interface DebugSettings {
  persistStore: boolean;
}
let debugSettings: DebugSettings | undefined = isDevelopment ? ipcRenderer.sendSync(IpcCommands.GET_DEBUG) : undefined;

if (isDevelopment) {
  ipcRenderer.on(IpcCommands.DEBUG_SETTINGS, (event, args) => {
    debugSettings = args;
  });
}

contextBridge.exposeInMainWorld('interop', {
  openUrl: (url: string) => ipcRenderer.send(IpcCommands.OPEN_URL, url),
  closeApp: () => ipcRenderer.send(IpcCommands.CLOSE_APP),
  openDirectory: async (title: string) => ipcAction(IpcCommands.OPEN_DIRECTORY, title),
  premiumUserLoggedIn: (premiumUser: boolean) => ipcRenderer.send(IpcCommands.PREMIUM_LOGIN, premiumUser),
  setListeners(listeners: Listeners): void {
    ipcRenderer.on('failed', (event, error, code) => {
      listeners.onError(error, code);
      ipcRenderer.send('ack', 1);
    });

    ipcRenderer.on(IpcCommands.REQUEST_RESTART, () => {
      listeners.onRestart();
    });

    ipcRenderer.on(IpcCommands.ABOUT, () => {
      listeners.onAbout();
    });

    ipcRenderer.on(IpcCommands.BACKEND_PROCESS_DETECTED, (_event, pids) => {
      listeners.onProcessDetected(pids);
    });
  },
  debugSettings: isDevelopment ? (): DebugSettings | undefined => debugSettings : undefined,
  serverUrl: (): string => ipcRenderer.sendSync(IpcCommands.SERVER_URL),
  metamaskImport: async () => ipcAction(IpcCommands.METAMASK_IMPORT),
  restartBackend: async options => ipcAction(IpcCommands.RESTART_BACKEND, options),
  checkForUpdates: async () => ipcAction(IpcCommands.CHECK_FOR_UPDATES),
  downloadUpdate: async (progress) => {
    ipcRenderer.on(IpcCommands.DOWNLOAD_PROGRESS, (event, args) => {
      progress(args);
    });
    return ipcAction(IpcCommands.DOWNLOAD_UPDATE);
  },
  installUpdate: async () => ipcAction(IpcCommands.INSTALL_UPDATE),
  setSelectedTheme: async selectedTheme => ipcAction(IpcCommands.THEME, selectedTheme),
  version: async () => ipcAction(IpcCommands.VERSION),
  isMac: async () => ipcAction(IpcCommands.IS_MAC),
  openPath: (path: string) => ipcRenderer.send(IpcCommands.OPEN_PATH, path),
  config: async (defaults: boolean) => ipcAction(IpcCommands.CONFIG, defaults),
  updateTray: (trayUpdate: TrayUpdate) => ipcRenderer.send(IpcCommands.TRAY_UPDATE, trayUpdate),
  logToFile(message: string) {
    ipcRenderer.send(IpcCommands.LOG_TO_FILE, message);
  },
  storePassword: async (username: string, password: string) => ipcAction(IpcCommands.STORE_PASSWORD, { username, password }),
  getPassword: async (username: string) => ipcAction(IpcCommands.GET_PASSWORD, username),
  clearPassword: async () => ipcAction(IpcCommands.CLEAR_PASSWORD),
} as Interop);
