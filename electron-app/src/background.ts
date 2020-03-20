'use strict';
import {
  app,
  protocol,
  BrowserWindow,
  Menu,
  ipcMain,
  shell,
  dialog
} from 'electron';
import {
  createProtocol,
  installVueDevtools
} from 'vue-cli-plugin-electron-builder/lib';
import PyHandler from './py-handler';
import MenuItemConstructorOptions = Electron.MenuItemConstructorOptions;
import windowStateKeeper from 'electron-window-state';
import path from 'path';

const isDevelopment = process.env.NODE_ENV !== 'production';

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

function createWindow() {
  // set default window Width and Height in case not specific
  let mainWindowState = windowStateKeeper({
    defaultWidth: 1200,
    defaultHeight: 800
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
      enableRemoteModule: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  if (process.env.WEBPACK_DEV_SERVER_URL) {
    pyHandler.setCorsURL(process.env.WEBPACK_DEV_SERVER_URL);
    // Load the url of the dev server if in development mode
    win.loadURL(process.env.WEBPACK_DEV_SERVER_URL);
    if (!process.env.IS_TEST) win.webContents.openDevTools();
  } else {
    createProtocol('app');
    // Load the index.html when not in development
    pyHandler.setCorsURL('app://*');
    win.loadURL('app://./index.html');
  }

  // Check if we are on a MAC
  if (process.platform === 'darwin') {
    // Create our menu entries so that we can use MAC shortcuts
    const template: MenuItemConstructorOptions[] = [
      {
        label: 'Edit',
        submenu: [
          { role: 'undo' },
          { role: 'redo' },
          { type: 'separator' },
          { role: 'cut' },
          { role: 'copy' },
          { role: 'paste' },
          { role: 'pasteAndMatchStyle' },
          { role: 'delete' },
          { role: 'selectAll' }
        ]
      }
    ];
    Menu.setApplicationMenu(Menu.buildFromTemplate(template));
  }

  // Register and deregister listeners to window events (resize, move, close) so that window state is saved
  mainWindowState.manage(win);

  win.on('closed', async () => {
    win = null;
  });

  pyHandler.createPyProc(win);
  pyHandler.listenForMessages();
}
// Quit when all windows are closed.
app.on('window-all-closed', () => {
  app.quit();
});
app.on('activate', () => {
  // On macOS it's common to re-create a window in the app when the
  // dock icon is clicked and there are no other windows open.
  if (win === null) {
    createWindow();
  }
});
// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
app.on('ready', async () => {
  if (isDevelopment && !process.env.IS_TEST) {
    // Install Vue Devtools
    try {
      await installVueDevtools();
    } catch (e) {
      console.error('Vue Devtools failed to install:', e.toString());
    }
  }
  ipcMain.on('CLOSE_APP', async () => await closeApp());
  ipcMain.on('OPEN_URL', (event, args) => {
    if (
      !(
        args.indexOf('https://rotki.com') > -1 ||
        args.indexOf('https://github.com/rotki/rotki/') > -1
      )
    ) {
      console.error(`Error: Requested to open untrusted URL: ${args} `);
      return;
    }
    shell.openExternal(args);
  });
  ipcMain.on('OPEN_FILE', async (event, args) => {
    const file = await select(args, 'openFile');
    event.sender.send('OPEN_FILE', file);
  });
  ipcMain.on('OPEN_DIRECTORY', async (event, args) => {
    const directory = await select(args, 'openDirectory');
    event.sender.send('OPEN_DIRECTORY', directory);
  });
  createWindow();
});

async function closeApp() {
  await pyHandler.exitPyProc();
  if (process.platform !== 'win32') {
    app.exit();
  }
}

app.on('will-quit', async e => {
  e.preventDefault();
  await closeApp();
});

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
