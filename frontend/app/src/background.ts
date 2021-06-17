import path from 'path';
import { app, BrowserWindow, Menu, protocol } from 'electron';
import installExtension, { VUEJS_DEVTOOLS } from 'electron-devtools-installer';
import windowStateKeeper from 'electron-window-state';
import { createProtocol } from 'vue-cli-plugin-electron-builder/lib';
import { ipcSetup } from '@/electron-main/ipc-setup';
import { getUserMenu } from '@/electron-main/menu';
import { TrayManager } from '@/electron-main/tray-manager';
import { Nullable } from '@/types';
import PyHandler from './py-handler';
import { assert } from './utils/assertions';

const isDevelopment = process.env.NODE_ENV !== 'production';

let trayManager: Nullable<TrayManager> = null;

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

  const getWindow = () => {
    const window = win;
    assert(window !== null);
    return window;
  };

  trayManager = new TrayManager(getWindow, closeApp);
  ipcSetup(pyHandler, getWindow, closeApp, trayManager);
  await createWindow();
  trayManager.listen();
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
  return win;
}

async function closeApp() {
  trayManager?.destroy();
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
