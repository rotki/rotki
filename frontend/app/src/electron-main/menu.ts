import { app, BrowserWindow, MenuItem, shell } from 'electron';
import { settingsManager } from '@/electron-main/app-settings';
import {
  IPC_ABOUT,
  IPC_DEBUG_SETTINGS,
  IPC_REQUEST_RESTART
} from '@/electron-main/ipc-commands';
import { checkIfDevelopment } from '@/utils/env-utils';

const isDevelopment = checkIfDevelopment();
const isMac = process.platform === 'darwin';

export type MenuActions = { displayTray: (display: boolean) => void };

export const debugSettings = {
  persistStore: false
};

let actions: MenuActions = { displayTray: () => {} };

const debugMenu = {
  label: '&Debug',
  submenu: [
    {
      label: 'Persist store',
      type: 'checkbox',
      checked: debugSettings.persistStore,
      click: async (item: MenuItem, browserWindow: BrowserWindow) => {
        debugSettings.persistStore = item.checked;
        browserWindow.webContents.send(IPC_DEBUG_SETTINGS, debugSettings);
        browserWindow.reload();
      }
    }
  ]
};

const separator = { type: 'separator' };

const helpMenu = {
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
      label: 'Frequently Asked Questions',
      click: async () => {
        await shell.openExternal(
          'https://rotki.readthedocs.io/en/latest/faq.html'
        );
      }
    },
    separator,
    {
      label: 'Release Notes',
      click: async () => {
        await shell.openExternal(
          'https://rotki.readthedocs.io/en/latest/changelog.html'
        );
      }
    },
    separator,
    {
      label: 'Issue / Feature Requests',
      click: async () => {
        await shell.openExternal('https://github.com/rotki/rotki/issues');
      }
    },
    {
      label: 'Logs Directory',
      click: async () => {
        await shell.openPath(app.getPath('logs'));
      }
    },
    separator,
    {
      label: 'Clear Cache',
      click: async (_item: MenuItem, browserWindow: BrowserWindow) => {
        await browserWindow.webContents.session.clearCache();
      }
    },
    {
      label: 'Reset Settings / Restart Backend',
      click: async (_item: MenuItem, browserWindow: BrowserWindow) => {
        await browserWindow.webContents.session.clearStorageData();
        browserWindow.webContents.send(IPC_REQUEST_RESTART);
      }
    },
    separator,
    {
      label: 'About',
      click: (_item: MenuItem, browserWindow: BrowserWindow) => {
        browserWindow.webContents.send(IPC_ABOUT);
      }
    }
  ]
};
const macEditOptions = [
  { role: 'pasteAndMatchStyle' },
  { role: 'delete' },
  { role: 'selectAll' },
  separator,
  {
    label: 'Speech',
    submenu: [{ role: 'startspeaking' }, { role: 'stopspeaking' }]
  }
];
const editMenu = {
  label: '&Edit',
  submenu: [
    { role: 'undo' },
    { role: 'redo' },
    separator,
    { role: 'cut' },
    { role: 'copy' },
    { role: 'paste' },
    // Macs have special copy/paste and speech functionality
    ...(isMac
      ? macEditOptions
      : [{ role: 'delete' }, separator, { role: 'selectAll' }])
  ]
};
const fileMenu = {
  label: 'File',
  submenu: [isMac ? { role: 'close' } : { role: 'quit' }]
};

const developmentViewMenu = [
  { role: 'reload' },
  { role: 'forceReload' },
  { role: 'toggleDevTools' },
  separator
];

const minimize = {
  id: 'MINIMIZE_TO_TRAY',
  label: 'Minimize to tray',
  enabled: settingsManager.appSettings.displayTray,
  click: (_: KeyboardEvent, window: BrowserWindow) => {
    window.hide();
  }
};

const displayTrayIcon = {
  label: 'Display Tray Icon',
  type: 'checkbox',
  checked: settingsManager.appSettings.displayTray,
  click: async (item: MenuItem) => {
    const displayTray = item.checked;
    settingsManager.appSettings.displayTray = displayTray;
    settingsManager.save();
    actions.displayTray(displayTray);
  }
};

const viewMenu = {
  label: '&View',
  submenu: [
    ...(isDevelopment
      ? developmentViewMenu
      : [{ role: 'toggleDevTools', visible: false }]),
    { role: 'resetZoom' },
    { role: 'zoomIn' },
    { role: 'zoomOut' },
    separator,
    { role: 'togglefullscreen' },
    minimize,
    separator,
    displayTrayIcon
  ]
};
const defaultMenuTemplate: any[] = [
  // On a mac we want to show a "rotki" menu item in the app bar
  ...(isMac
    ? [
        {
          label: app.name,
          submenu: [
            { role: 'hide' },
            { role: 'hideOthers' },
            { role: 'unhide' },
            separator,
            { role: 'quit' }
          ]
        }
      ]
    : []),
  fileMenu,
  editMenu,
  viewMenu,
  helpMenu,
  separator,

  ...(isDevelopment ? [debugMenu] : [])
];

export function getUserMenu(showPremium: boolean, menuActions: MenuActions) {
  actions = menuActions;
  const getRotkiPremiumButton = {
    label: '&Get rotki Premium',
    ...(isMac
      ? {
          // submenu is mandatory to be displayed on macOS
          submenu: [
            {
              label: 'Get rotki Premium',
              id: 'premium-button',
              click: () => {
                shell.openExternal('https://rotki.com/products/');
              }
            }
          ]
        }
      : {
          id: 'premium-button',
          click: () => {
            shell.openExternal('https://rotki.com/products/');
          }
        })
  };

  // Re-render the menu with the 'Get rotki Premium' button if the user who just logged in
  // is not a premium user, otherwise render the menu without the button. Since we are unable to just toggle
  // visibility on a top-level menu item, we instead have to add/remove it from the menu upon every login
  // (see https://github.com/electron/electron/issues/8703). TODO: if we move the menu to the render
  // process we can make this a lot cleaner.

  return showPremium
    ? defaultMenuTemplate.concat(getRotkiPremiumButton)
    : defaultMenuTemplate;
}
