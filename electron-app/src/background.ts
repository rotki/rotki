'use strict';
import path from 'path';
import {
  app,
  protocol,
  BrowserWindow,
  Menu,
  ipcMain,
  shell,
  dialog
} from 'electron';
import windowStateKeeper from 'electron-window-state';
import {
  createProtocol,
  installVueDevtools
} from 'vue-cli-plugin-electron-builder/lib';
import PyHandler from './py-handler';
import MenuItemConstructorOptions = Electron.MenuItemConstructorOptions;

const isDevelopment = process.env.NODE_ENV !== 'production';
const isMac = process.platform === 'darwin';

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

const defaultMenuTemplate: any[] = [
  // On a mac we want to show a "Rotki" menu item in the app bar
  ...(isMac
    ? [
        {
          label: app.name,
          submenu: [
            { role: 'hide' },
            { role: 'hideOthers' },
            { role: 'unhide' },
            { type: 'separator' },
            { role: 'quit' }
          ]
        }
      ]
    : []),
  {
    label: 'File',
    submenu: [isMac ? { role: 'close' } : { role: 'quit' }]
  },

  {
    label: '&Edit',
    submenu: [
      { role: 'undo' },
      { role: 'redo' },
      { type: 'separator' },
      { role: 'cut' },
      { role: 'copy' },
      { role: 'paste' },
      // Macs have special copy/paste and speech functionality
      ...(isMac
        ? [
            { role: 'pasteAndMatchStyle' },
            { role: 'delete' },
            { role: 'selectAll' },
            { type: 'separator' },
            {
              label: 'Speech',
              submenu: [{ role: 'startspeaking' }, { role: 'stopspeaking' }]
            }
          ]
        : [{ role: 'delete' }, { type: 'separator' }, { role: 'selectAll' }])
    ]
  },
  {
    label: '&View',
    submenu: [
      { role: 'reload' },
      { role: 'forceReload' },
      { role: 'toggleDevTools' },
      { type: 'separator' },
      { role: 'resetZoom' },
      { role: 'zoomIn' },
      { role: 'zoomOut' },
      { type: 'separator' },
      { role: 'togglefullscreen' }
    ]
  },
  {
    label: '&Help',
    submenu: [
      {
        label: 'Usage Guide',
        click: async () => {
          await shell.openExternal(
            'https://rotki.readthedocs.io/en/latest/usage_guide.html'
          );
        }
      },
      {
        label: 'Frequenty Asked Questions',
        click: async () => {
          await shell.openExternal(
            'https://rotki.readthedocs.io/en/latest/faq.html'
          );
        }
      },
      { type: 'separator' },
      {
        label: 'Release Notes',
        click: async () => {
          await shell.openExternal(
            'https://rotki.readthedocs.io/en/latest/changelog.html'
          );
        }
      },
      { type: 'separator' },
      {
        label: 'Issue / Feature Requests',
        click: async () => {
          await shell.openExternal('https://github.com/rotki/rotki/issues');
        }
      },
      {
        label: 'Logs Directory',
        click: () => {
          shell.openItem(app.getPath('logs'));
        }
      }
    ]
  },
  {
    type: 'separator'
  }
];

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

  const menuTemplate: MenuItemConstructorOptions[] = defaultMenuTemplate as MenuItemConstructorOptions[];
  Menu.setApplicationMenu(Menu.buildFromTemplate(menuTemplate));

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
  ipcMain.on('PREMIUM_USER_LOGGED_IN', (event, args) => {
    const getRotkiPremiumButton = {
      label: '&Get Rotki Premium',
      id: 'premium-button',
      click: () => {
        shell.openExternal('https://rotki.com/products/');
      }
    };

    // Re-render the menu with the 'Get Rotki Premium' button if the user who just logged in
    // is not a premium user, otherwise render the menu without the button. Since we are unable to just toggle
    // visibility on a top-level menu item, we instead have to add/remove it from the menu upon every login
    // (see https://github.com/electron/electron/issues/8703). TODO: if we move the menu to the render
    // process we can make this a lot cleaner.
    if (args === false) {
      const newMenuTemplate = defaultMenuTemplate.concat(getRotkiPremiumButton);
      Menu.setApplicationMenu(Menu.buildFromTemplate(newMenuTemplate));
    } else {
      Menu.setApplicationMenu(Menu.buildFromTemplate(defaultMenuTemplate));
    }
  });
  ipcMain.on('CLOSE_APP', async () => await closeApp());
  ipcMain.on('OPEN_URL', (event, args) => {
    if (
      !(
        args.indexOf('https://rotki.com') > -1 ||
        args.indexOf('https://rotki.readthedocs.io/') > -1 ||
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
