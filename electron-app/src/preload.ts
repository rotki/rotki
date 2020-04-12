import { contextBridge, ipcRenderer } from 'electron';

function ipcAction(message: string, title: string) {
  return new Promise(resolve => {
    ipcRenderer.on(message, (event, args) => {
      resolve(args);
    });
    ipcRenderer.send(message, title);
  });
}

contextBridge.exposeInMainWorld('interop', {
  openUrl: (url: string) => ipcRenderer.send('OPEN_URL', url),
  closeApp: () => ipcRenderer.send('CLOSE_APP'),
  openFile: (title: string) => ipcAction('OPEN_FILE', title),
  openDirectory: (title: string) => ipcAction('OPEN_DIRECTORY', title),
  premiumUserLoggedIn: (premiumUser: boolean) => ipcRenderer.send('PREMIUM_USER_LOGGED_IN', premiumUser),
  listenForErrors: (callback: () => void) => {
    ipcRenderer.on('failed', () => {
      callback();
      ipcRenderer.send('ack', 1);
    });
  }
});
