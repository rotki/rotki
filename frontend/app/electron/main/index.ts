import path from 'node:path';
import process from 'node:process';
import { BrowserWindow, Menu, MenuItem, app, protocol, screen } from 'electron';
import windowStateKeeper from 'electron-window-state';
import { type Nullable, assert } from '@rotki/common';
import { ipcSetup } from '@electron/main/ipc-setup';
import { getUserMenu } from '@electron/main/menu';
import { TrayManager } from '@electron/main/tray-manager';
import { startPromise } from '@shared/utils';
import { createProtocol } from '@electron/main/create-protocol';
import { SubprocessHandler } from '@electron/main/subprocess-handler';

let trayManager: Nullable<TrayManager> = null;
let forceQuit = false;
let win: BrowserWindow | null;
// Keep a global reference of the window object, if you don't, the window will
// be closed automatically when the JavaScript object is garbage collected.
const pyHandler = new SubprocessHandler(app);

const isMac = process.platform === 'darwin';

const menuActions = {
  displayTray: (display: boolean): void => {
    const applicationMenu = Menu.getApplicationMenu();
    if (applicationMenu) {
      const menuItem = applicationMenu.getMenuItemById('MINIMIZE_TO_TRAY');
      if (menuItem)
        menuItem.enabled = display;
    }

    if (display)
      trayManager?.build();
    else trayManager?.destroy();
  },
};

async function onActivate(): Promise<void> {
  // On macOS it's common to re-create a window in the app when the
  // dock icon is clicked and there are no other windows open.
  if (win === null)
    await createWindow();
  else win?.show();
}

// Some APIs can only be used after this event occurs.
async function onReady(): Promise<void> {
  const getWindow = () => {
    const window = win;
    assert(window !== null);
    return window;
  };

  trayManager = new TrayManager(getWindow, closeApp);
  ipcSetup(pyHandler, getWindow, closeApp, trayManager, menuActions, ensureSafeUpdateRestart);
  await createWindow();
  trayManager.listen();

  getWindow().webContents.on('context-menu', (_event, props): void => {
    const menu = new Menu();
    if (props.editFlags.canCut)
      menu.append(new MenuItem({ label: 'Cut', role: 'cut' }));

    if (props.editFlags.canCopy)
      menu.append(new MenuItem({ label: 'Copy', role: 'copy' }));

    if (props.editFlags.canPaste)
      menu.append(new MenuItem({ label: 'Paste', role: 'paste' }));

    menu.popup({ window: getWindow() });
  });

  getWindow().webContents.on('before-input-event', (event, input) => {
    const win = getWindow();
    if (isMac ? input.meta : input.control) {
      if (['ArrowLeft', '['].includes(input.key) && win.webContents.canGoBack()) {
        win.webContents.goBack();
        event.preventDefault();
      }

      if (['ArrowRight', ']'].includes(input.key) && win.webContents.canGoForward()) {
        win.webContents.goForward();
        event.preventDefault();
      }
    }
  });
}

const lock = app.requestSingleInstanceLock();

if (!lock) {
  app.quit();
}
else {
  app.on('second-instance', (): void => {
    try {
      if (!win)
        return;

      if (win.isMinimized())
        win.restore();

      win.focus();
    }
    catch (error) {
      console.error('Could not restore the window', error);
      app.quit();
    }
  });

  // Quit when all windows are closed.
  app.on('window-all-closed', (): void => {
    if (!isMac)
      app.quit();
  });
  app.on('activate', () => startPromise(onActivate()));
  app.on('ready', () => startPromise(onReady()));
  app.on('will-quit', (e) => {
    e.preventDefault();
    startPromise(closeApp());
  });
  app.on('before-quit', (): void => {
    pyHandler.quitting();
    forceQuit = true;
  });
}

function ensureSafeUpdateRestart(): void {
  win?.removeAllListeners('close');
  win?.removeAllListeners('closed');
  app.removeAllListeners('close');
  app.removeAllListeners('window-all-closed');
  app.removeAllListeners('will-quit');
  app.removeAllListeners('before-quit');
}

// Standard scheme must be registered before the app is ready
protocol.registerSchemesAsPrivileged([
  {
    scheme: 'app',
    privileges: { standard: true, secure: true, supportFetchAPI: true },
  },
]);

async function createWindow(): Promise<BrowserWindow> {
  const { width: screenWidth, height: screenHeight } = screen.getPrimaryDisplay().workAreaSize;

  const regularScreenWidth = 1366;
  const regularScreenHeight = 768;

  const minimumWidth = 1200;
  const ratio = regularScreenWidth / minimumWidth;
  const minimumHeight = regularScreenHeight / ratio;

  const defaultWidth = Math.floor(Math.max(screenWidth / ratio, minimumWidth));
  const defaultHeight = Math.floor(Math.max(screenHeight / ratio, minimumHeight));

  // set default window width and height to be proportional with screen resolution, in case not specified
  // A = regular screen size
  // B = minimum window size
  // C = screen resolution
  // D = expected window size
  // A / B = C / D
  const mainWindowState = windowStateKeeper({
    defaultWidth,
    defaultHeight,
  });

  // Create the browser window.
  win = new BrowserWindow({
    x: mainWindowState.x, // defaults to middle of the screen if not specified
    y: mainWindowState.y, // defaults to middle of the screen if not specified
    width: mainWindowState.width,
    height: mainWindowState.height,
    webPreferences: {
      nodeIntegration: false,
      sandbox: true,
      contextIsolation: true,
      preload: path.join(import.meta.dirname, 'preload.js'),
    },
  });

  if (import.meta.env.VITE_DEV_SERVER_URL) {
    pyHandler.setCorsURL(import.meta.env.VITE_DEV_SERVER_URL as string);
    // Load the url of the dev server if in development mode
    await win.loadURL(import.meta.env.VITE_DEV_SERVER_URL as string);
    if (process.env.ENABLE_DEV_TOOLS)
      win.webContents.openDevTools();
  }
  else {
    createProtocol('app');
    // Load the index.html when not in development
    pyHandler.setCorsURL('app://*');
    await win.loadURL('app://./index.html');
  }

  Menu.setApplicationMenu(Menu.buildFromTemplate(getUserMenu(true, menuActions)));
  // Register and deregister listeners to window events (resize, move, close) so that window state is saved
  mainWindowState.manage(win);

  async function close(e: Electron.Event) {
    try {
      if (isMac && !forceQuit) {
        e.preventDefault();
        win?.hide();
      }
      else {
        await closeApp();
      }
    }
    catch (error) {
      console.error(error);
      await closeApp();
    }
  }

  win.on('close', e => startPromise(close(e)));

  win.on('closed', () => {
    try {
      if (isMac && !forceQuit)
        win?.hide();
      else win = null;
    }
    catch (error) {
      console.error(error);
    }
  });
  return win;
}

async function closeApp(): Promise<void> {
  trayManager?.destroy();
  try {
    await pyHandler.exitPyProc();
  }
  finally {
    // In some cases app object might be already disposed
    try {
      if (process.platform !== 'win32')
        app.exit();
    }
    catch (error: any) {
      if (error.message !== 'Object has been destroyed')
        console.error(error);
    }
  }
}
