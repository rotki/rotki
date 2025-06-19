import type { ApiUrls, Credentials, Interop, Listeners, TrayUpdate } from '@shared/ipc';
import type { LogLevel } from '@shared/log-level';
import { IpcCommands } from '@electron/ipc-commands';
import { checkIfDevelopment } from '@shared/utils';
import { contextBridge, ipcRenderer } from 'electron';

const isDevelopment = checkIfDevelopment();

interface DebugSettings {
  persistStore: boolean;
}

let debugSettings: DebugSettings | undefined = isDevelopment ? ipcRenderer.sendSync(IpcCommands.SYNC_GET_DEBUG) : undefined;

if (isDevelopment) {
  ipcRenderer.on(IpcCommands.DEBUG_SETTINGS, (event, args) => {
    debugSettings = args;
  });
}

contextBridge.exposeInMainWorld('interop', {
  openUrl: async (url: string) => ipcRenderer.invoke(IpcCommands.INVOKE_OPEN_URL, url),
  closeApp: async () => ipcRenderer.invoke(IpcCommands.INVOKE_CLOSE_APP),
  openDirectory: async (title: string) => ipcRenderer.invoke(IpcCommands.INVOKE_OPEN_DIRECTORY, title),
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

    if (listeners.onOAuthCallback) {
      ipcRenderer.on('oauth-callback', (_event, accessTokenOrError) => {
        listeners.onOAuthCallback!(accessTokenOrError);
      });
    }
  },
  debugSettings: isDevelopment ? (): DebugSettings | undefined => debugSettings : undefined,
  apiUrls: (): ApiUrls => ipcRenderer.sendSync(IpcCommands.SYNC_API_URL),
  metamaskImport: async () => ipcRenderer.invoke(IpcCommands.INVOKE_WALLET_IMPORT),
  openWalletConnectBridge: async () => ipcRenderer.invoke(IpcCommands.OPEN_WALLET_CONNECT_BRIDGE),
  restartBackend: async options => ipcRenderer.invoke(IpcCommands.INVOKE_SUBPROCESS_START, options),
  checkForUpdates: async () => ipcRenderer.invoke(IpcCommands.INVOKE_UPDATE_CHECK),
  downloadUpdate: async (progress) => {
    ipcRenderer.on(IpcCommands.DOWNLOAD_PROGRESS, (event, args) => {
      progress(args);
    });
    return ipcRenderer.invoke(IpcCommands.INVOKE_DOWNLOAD_UPDATE);
  },
  installUpdate: async () => ipcRenderer.invoke(IpcCommands.INVOKE_INSTALL_UPDATE),
  setSelectedTheme: async selectedTheme => ipcRenderer.invoke(IpcCommands.INVOKE_THEME, selectedTheme),
  version: async () => ipcRenderer.invoke(IpcCommands.INVOKE_VERSION),
  isMac: async () => ipcRenderer.invoke(IpcCommands.INVOKE_IS_MAC),
  openPath: async (path: string) => ipcRenderer.invoke(IpcCommands.INVOKE_OPEN_PATH, path),
  config: async (defaults: boolean) => ipcRenderer.invoke(IpcCommands.INVOKE_CONFIG, defaults),
  updateTray: (trayUpdate: TrayUpdate) => ipcRenderer.send(IpcCommands.TRAY_UPDATE, trayUpdate),
  logToFile: (level: LogLevel, message: string) => {
    ipcRenderer.send(IpcCommands.LOG_TO_FILE, level, message);
  },
  storePassword: async (credentials: Credentials) => ipcRenderer.invoke(IpcCommands.INVOKE_STORE_PASSWORD, credentials),
  getPassword: async (username: string) => ipcRenderer.invoke(IpcCommands.INVOKE_GET_PASSWORD, username),
  clearPassword: async () => ipcRenderer.invoke(IpcCommands.INVOKE_CLEAR_PASSWORD),
} satisfies Interop);
