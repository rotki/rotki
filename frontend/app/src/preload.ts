import { contextBridge, ipcRenderer } from 'electron';

function ipcAction(message: string, title: string) {
  return new Promise(resolve => {
    ipcRenderer.on(message, (event, args) => {
      resolve(args);
    });
    ipcRenderer.send(message, title);
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
  openFile: (title: string) => ipcAction('OPEN_FILE', title),
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
    : undefined
});
