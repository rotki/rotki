import path from 'node:path';
import { BrowserWindow, Menu, MenuItem, app, protocol, screen } from 'electron';
import windowStateKeeper from 'electron-window-state';
import { ipcSetup } from '@/electron-main/ipc-setup';
import { getUserMenu } from '@/electron-main/menu';
import { TrayManager } from '@/electron-main/tray-manager';
import { type Nullable } from '@/types';
import { checkIfDevelopment } from '@/utils/env-utils';
import createProtocol from './create-protocol';
import SubprocessHandler from './subprocess-handler';
import { assert } from './utils/assertions';

const isDevelopment = checkIfDevelopment();

let trayManager: Nullable<TrayManager> = null;
let forceQuit = false;

const onActivate = async (): Promise<void> => {
  // On macOS it's common to re-create a window in the app when the
  // dock icon is clicked and there are no other windows open.
  if (win === null) {
    await createWindow();
  } else {
    win?.show();
  }
};

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
const onReady = async (): Promise<void> => {
  if (isDevelopment) {
    // Install Vue Devtools
    try {
      // Vite 4.x and cjs module (figure out if there is a better solution)
      const { VUEJS_DEVTOOLS, default: tools } = await import(
        'electron-devtools-installer'
      );
      if ('default' in tools && typeof tools.default === 'function') {
        await tools.default(VUEJS_DEVTOOLS);
      } else if (typeof tools === 'function') {
        await tools(VUEJS_DEVTOOLS);
      } else {
        console.error('something is wrong with devtools installer');
      }
    } catch (e: any) {
      console.error('Vue Devtools failed to install:', e.toString());
    }
  }

  const getWindow = () => {
    const window = win;
    assert(window !== null);
    return window;
  };

  trayManager = new TrayManager(getWindow, closeApp);
  ipcSetup(
    pyHandler,
    getWindow,
    closeApp,
    trayManager,
    menuActions,
    ensureSafeUpdateRestart
  );
  await createWindow();
  trayManager.listen();

  getWindow().webContents.on('context-menu', (event, props): void => {
    const menu = new Menu();
    if (props.editFlags.canCut) {
      menu.append(new MenuItem({ label: 'Cut', role: 'cut' }));
    }

    if (props.editFlags.canCopy) {
      menu.append(new MenuItem({ label: 'Copy', role: 'copy' }));
    }

    if (props.editFlags.canPaste) {
      menu.append(new MenuItem({ label: 'Paste', role: 'paste' }));
    }

    menu.popup({ window: getWindow() });
  });
};

const lock = app.requestSingleInstanceLock();

if (!lock) {
  app.quit();
} else {
  app.on('second-instance', (): void => {
    try {
      if (!win) {
        return;
      }

      if (win.isMinimized()) {
        win.restore();
      }
      win.focus();
    } catch (e) {
      console.error('Could not restore the window', e);
      app.quit();
    }
  });

  // Quit when all windows are closed.
  app.on('window-all-closed', (): void => {
    if (process.platform !== 'darwin') {
      app.quit();
    }
  });
  app.on('activate', onActivate);
  app.on('ready', onReady);
  app.on('will-quit', async e => {
    e.preventDefault();
    await closeApp();
  });
  app.on('before-quit', (): void => {
    forceQuit = true;
  });
}

const ensureSafeUpdateRestart = (): void => {
  win?.removeAllListeners('close');
  win?.removeAllListeners('closed');
  app.removeAllListeners('close');
  app.removeAllListeners('window-all-closed');
  app.removeAllListeners('will-quit');
  app.removeAllListeners('before-quit');
};

const menuActions = {
  displayTray: (display: boolean): void => {
    const applicationMenu = Menu.getApplicationMenu();
    if (applicationMenu) {
      const menuItem = applicationMenu.getMenuItemById('MINIMIZE_TO_TRAY');
      if (menuItem) {
        menuItem.enabled = display;
      }
    }

    if (display) {
      trayManager?.build();
    } else {
      trayManager?.destroy();
    }
  }
};

// Keep a global reference of the window object, if you don't, the window will
// be closed automatically when the JavaScript object is garbage collected.
let win: BrowserWindow | null;
const pyHandler = new SubprocessHandler(app);

// Standard scheme must be registered before the app is ready
protocol.registerSchemesAsPrivileged([
  {
    scheme: 'app',
    privileges: { standard: true, secure: true, supportFetchAPI: true }
  }
]);

async function createWindow(): Promise<BrowserWindow> {
  const { width: screenWidth, height: screenHeight } =
    screen.getPrimaryDisplay().workAreaSize;

  const regularScreenWidth = 1366;
  const regularScreenHeight = 768;

  const minimumWidth = 1200;
  const ratio = regularScreenWidth / minimumWidth;
  const minimumHeight = regularScreenHeight / ratio;

  const defaultWidth = Math.floor(Math.max(screenWidth / ratio, minimumWidth));
  const defaultHeight = Math.floor(
    Math.max(screenHeight / ratio, minimumHeight)
  );

  // set default window width and height to be proportional with screen resolution, in case not specified
  // A = regular screen size
  // B = minimum window size
  // C = screen resolution
  // D = expected window size
  // A / B = C / D
  const mainWindowState = windowStateKeeper({
    defaultWidth,
    defaultHeight
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
      preload: path.join(__dirname, 'preload.js')
    }
  });

  if (import.meta.env.VITE_DEV_SERVER_URL) {
    pyHandler.setCorsURL(import.meta.env.VITE_DEV_SERVER_URL as string);
    // Load the url of the dev server if in development mode
    await win.loadURL(import.meta.env.VITE_DEV_SERVER_URL as string);
    win.webContents.openDevTools();
  } else {
    createProtocol('app');
    // Load the index.html when not in development
    pyHandler.setCorsURL('app://*');
    await win.loadURL('app://./index.html');
  }

  Menu.setApplicationMenu(
    Menu.buildFromTemplate(getUserMenu(true, menuActions))
  );
  // Register and deregister listeners to window events (resize, move, close) so that window state is saved
  mainWindowState.manage(win);

  win.on('close', async e => {
    try {
      if (process.platform === 'darwin' && !forceQuit) {
        e.preventDefault();
        win?.hide();
      } else {
        await closeApp();
      }
    } catch (e) {
      console.error(e);
      await closeApp();
    }
  });

  win.on('closed', async () => {
    try {
      if (process.platform === 'darwin' && !forceQuit) {
        win?.hide();
      } else {
        win = null;
      }
    } catch (e) {
      console.error(e);
    }
  });
  return win;
}

async function closeApp(): Promise<void> {
  trayManager?.destroy();
  try {
    await pyHandler.exitPyProc();
  } finally {
    // In some cases app object might be already disposed
    try {
      if (process.platform !== 'win32') {
        app.exit();
      }
    } catch (e: any) {
      if (e.message !== 'Object has been destroyed') {
        console.error(e);
      }
    }
  }
}
