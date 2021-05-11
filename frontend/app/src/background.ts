import path from 'path';
import {
  app,
  BrowserWindow,
  dialog,
  ipcMain,
  Menu,
  nativeTheme,
  protocol,
  shell
} from 'electron';
import { ProgressInfo } from 'electron-builder';
import installExtension, { VUEJS_DEVTOOLS } from 'electron-devtools-installer';
import { autoUpdater } from 'electron-updater';
import windowStateKeeper from 'electron-window-state';
import { createProtocol } from 'vue-cli-plugin-electron-builder/lib';
import { startHttp, stopHttp } from '@/electron-main/http';
import {
  IPC_CHECK_FOR_UPDATES,
  IPC_DARK_MODE,
  IPC_DOWNLOAD_PROGRESS,
  IPC_DOWNLOAD_UPDATE,
  IPC_INSTALL_UPDATE,
  IPC_RESTART_BACKEND,
  IPC_VERSION,
  SystemVersion
} from '@/electron-main/ipc';
import { debugSettings, getUserMenu } from '@/electron-main/menu';
import { selectPort } from '@/electron-main/port-utils';
import { assert } from '@/utils/assertions';
import PyHandler from './py-handler';
import Timeout = NodeJS.Timeout;

const isDevelopment = process.env.NODE_ENV !== 'production';

const onActivate = async () => {
  // On macOS it's common to re-create a window in the app when the
  // dock icon is clicked and there are no other windows open.
  if (win === null) {
    await createWindow();
  }
};

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
const onReady = async () => {
  if (isDevelopment && !process.env.IS_TEST) {
    // Install Vue Devtools
    try {
      await installExtension(VUEJS_DEVTOOLS);
    } catch (e) {
      console.error('Vue Devtools failed to install:', e.toString());
    }
  }

  ipcMain.on('GET_DEBUG', event => {
    event.returnValue = debugSettings;
  });

  ipcMain.on('SERVER_URL', event => {
    event.returnValue = pyHandler.serverUrl;
  });

  ipcMain.on('PREMIUM_USER_LOGGED_IN', (event, args) => {
    Menu.setApplicationMenu(Menu.buildFromTemplate(getUserMenu(!args)));
  });
  ipcMain.on('CLOSE_APP', async () => await closeApp());
  ipcMain.on('OPEN_URL', (event, args) => {
    if (!args.startsWith('https://')) {
      console.error(`Error: Requested to open untrusted URL: ${args} `);
      return;
    }
    shell.openExternal(args);
  });
  ipcMain.on('OPEN_DIRECTORY', async (event, args) => {
    const directory = await select(args, 'openDirectory');
    event.sender.send('OPEN_DIRECTORY', directory);
  });
  let importTimeout: Timeout;
  ipcMain.on('METAMASK_IMPORT', async (event, _args) => {
    try {
      const port = startHttp(
        addresses => event.sender.send('METAMASK_IMPORT', { addresses }),
        await selectPort(40000)
      );
      await shell.openExternal(`http://localhost:${port}`);
      if (importTimeout) {
        clearTimeout(importTimeout);
      }
      importTimeout = setTimeout(() => {
        stopHttp();
        event.sender.send('METAMASK_IMPORT', { error: 'waiting timeout' });
      }, 120000);
    } catch (e) {
      event.sender.send('METAMASK_IMPORT', { error: e.message });
    }
  });

  ipcMain.on(IPC_RESTART_BACKEND, async (event, args) => {
    let success = false;
    try {
      assert(win);
      await pyHandler.exitPyProc(true);
      await pyHandler.createPyProc(win, args);
      success = true;
    } catch (e) {
      console.error(e);
    }

    event.sender.send(IPC_RESTART_BACKEND, success);
  });

  ipcMain.on(IPC_VERSION, event => {
    const version: SystemVersion = {
      os: process.platform,
      arch: process.arch,
      osVersion: process.getSystemVersion(),
      electron: process.versions.electron
    };
    event.sender.send(IPC_VERSION, version);
  });

  setupUpdaterInterop();
  await createWindow();
};

const lock = app.requestSingleInstanceLock();

if (!lock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (!win) {
      return;
    }

    if (win.isMinimized()) {
      win.restore();
    }
    win.focus();
  });

  // Quit when all windows are closed.
  app.on('window-all-closed', () => app.quit());
  app.on('activate', onActivate);
  app.on('ready', onReady);
  app.on('will-quit', async e => {
    e.preventDefault();
    await closeApp();
  });
}

async function select(
  title: string,
  prop: 'openFile' | 'openDirectory'
): Promise<string | undefined> {
  const value = await dialog.showOpenDialog({
    title,
    properties: [prop]
  });

  if (value.canceled) {
    return undefined;
  }
  return value.filePaths?.[0];
}

function setupUpdaterInterop() {
  autoUpdater.autoDownload = false;
  autoUpdater.logger = {
    error: (message?: any) => pyHandler.logToFile(`(error): ${message}`),
    info: (message?: any) => pyHandler.logToFile(`(info): ${message}`),
    debug: (message: string) => pyHandler.logToFile(`(debug): ${message}`),
    warn: (message?: any) => pyHandler.logToFile(`(warn): ${message}`)
  };
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
    } catch (e) {
      console.error(e);
      pyHandler.logToFile(e);
      event.sender.send(IPC_CHECK_FOR_UPDATES, false);
    }
  });

  ipcMain.on(IPC_DOWNLOAD_UPDATE, async event => {
    const progress = (progress: ProgressInfo) => {
      event.sender.send(IPC_DOWNLOAD_PROGRESS, progress.percent);
      win?.setProgressBar(progress.percent);
    };
    autoUpdater.on('download-progress', progress);
    try {
      await autoUpdater.downloadUpdate();
      event.sender.send(IPC_DOWNLOAD_UPDATE, true);
    } catch (e) {
      pyHandler.logToFile(e);
      event.sender.send(IPC_DOWNLOAD_UPDATE, false);
    } finally {
      autoUpdater.off('download-progress', progress);
    }
  });

  ipcMain.on(IPC_INSTALL_UPDATE, async event => {
    const quit = new Promise<void>((resolve, reject) => {
      const quitAndInstall = () => {
        try {
          autoUpdater.quitAndInstall();
          resolve();
        } catch (e) {
          pyHandler.logToFile(e);
          reject(e);
        }
      };
      return setTimeout(quitAndInstall, 5000);
    });
    try {
      await quit;
      event.sender.send(IPC_INSTALL_UPDATE, true);
    } catch (e) {
      pyHandler.logToFile(e);
      event.sender.send(IPC_INSTALL_UPDATE, e);
    }
  });

  ipcMain.on(IPC_DARK_MODE, async (event, enabled) => {
    if (enabled) {
      nativeTheme.themeSource = 'dark';
    } else {
      nativeTheme.themeSource = 'light';
    }
    event.sender.send(IPC_DARK_MODE, nativeTheme.shouldUseDarkColors);
  });
}

// Keep a global reference of the window object, if you don't, the window will
// be closed automatically when the JavaScript object is garbage collected.
let win: BrowserWindow | null;
const pyHandler = new PyHandler(app);

// Standard scheme must be registered before the app is ready
protocol.registerSchemesAsPrivileged([
  {
    scheme: 'app',
    privileges: { standard: true, secure: true, supportFetchAPI: true }
  }
]);

async function createWindow() {
  // set default window Width and Height in case not specific
  const mainWindowState = windowStateKeeper({
    defaultWidth: 1200,
    defaultHeight: 800
  });

  // Create the browser window.
  win = new BrowserWindow({
    x: mainWindowState.x, // defaults to middle of the screen if not specified
    y: mainWindowState.y, // defaults to middle of the screen if not specifiede
    width: mainWindowState.width,
    height: mainWindowState.height,
    webPreferences: {
      nodeIntegration: false,
      sandbox: true,
      enableRemoteModule: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  if (process.env.WEBPACK_DEV_SERVER_URL) {
    pyHandler.setCorsURL(process.env.WEBPACK_DEV_SERVER_URL);
    // Load the url of the dev server if in development mode
    await win.loadURL(process.env.WEBPACK_DEV_SERVER_URL);
    if (!process.env.IS_TEST) win.webContents.openDevTools();
  } else {
    createProtocol('app');
    // Load the index.html when not in development
    pyHandler.setCorsURL('app://*');
    await win.loadURL('app://./index.html');
  }

  Menu.setApplicationMenu(Menu.buildFromTemplate(getUserMenu(true)));
  // Register and deregister listeners to window events (resize, move, close) so that window state is saved
  mainWindowState.manage(win);

  win.on('closed', async () => {
    win = null;
  });
}

async function closeApp() {
  await pyHandler.exitPyProc();
  if (process.platform !== 'win32') {
    app.exit();
  }
}

// Exit cleanly on request from parent process in development mode.
if (isDevelopment) {
  if (process.platform === 'win32') {
    process.on('message', data => {
      if (data === 'graceful-exit') {
        app.quit();
      }
    });
  } else {
    process.on('SIGTERM', () => {
      app.quit();
    });
  }
}
