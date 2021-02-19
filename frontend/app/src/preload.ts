import { contextBridge, ipcRenderer } from 'electron';
import {
  Interop,
  IPC_CHECK_FOR_UPDATES,
  IPC_DOWNLOAD_UPDATE,
  IPC_INSTALL_UPDATE,
  IPC_RESTART_BACKEND
} from '@/electron-main/ipc';

function ipcAction<T>(message: string, arg?: any): Promise<T> {
  return new Promise(resolve => {
    ipcRenderer.on(message, (event, args) => {
      resolve(args);
    });
    ipcRenderer.send(message, arg);
  });
}

const isDevelopment = process.env.NODE_ENV !== 'production';

type DebugSettings = { vuex: boolean };
let debugSettings: DebugSettings | undefined = isDevelopment
  ? ipcRenderer.sendSync('GET_DEBUG')
  : undefined;

if (isDevelopment) {
  ipcRenderer.on('DEBUG_SETTINGS', (event, args) => {
    debugSettings = args;
  });
}

contextBridge.exposeInMainWorld('interop', {
  openUrl: (url: string) => ipcRenderer.send('OPEN_URL', url),
  closeApp: () => ipcRenderer.send('CLOSE_APP'),
  openDirectory: (title: string) => ipcAction('OPEN_DIRECTORY', title),
  premiumUserLoggedIn: (premiumUser: boolean) =>
    ipcRenderer.send('PREMIUM_USER_LOGGED_IN', premiumUser),
  listenForErrors: (callback: (backendOutput: string) => void) => {
    ipcRenderer.on('failed', (event, args) => {
      callback(args);
      ipcRenderer.send('ack', 1);
    });
  },
  debugSettings: isDevelopment
    ? (): DebugSettings | undefined => {
        return debugSettings;
      }
    : undefined,
  serverUrl: (): string => ipcRenderer.sendSync('SERVER_URL'),
  metamaskImport: () => ipcAction('METAMASK_IMPORT'),
  restartBackend: level => ipcAction(IPC_RESTART_BACKEND, level),
  checkForUpdates: () => ipcAction(IPC_CHECK_FOR_UPDATES),
  downloadUpdate: () => ipcAction(IPC_DOWNLOAD_UPDATE),
  installUpdate: () => ipcRenderer.send(IPC_INSTALL_UPDATE)
} as Interop);
