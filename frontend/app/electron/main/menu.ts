import type { AppConfig } from '@electron/main/app-config';
import type { LogService } from '@electron/main/log-service';
import type { SettingsManager } from '@electron/main/settings-manager';
import { IpcCommands } from '@electron/ipc-commands';
import { assert } from '@rotki/common';
import { externalLinks } from '@shared/external-links';
import { app, type BaseWindow, BrowserWindow, Menu, type MenuItem, type MenuItemConstructorOptions, shell } from 'electron';

interface MenuManagerListener {
  onDisplayTrayChanged: (displayTray: boolean) => void;
}

export class MenuManager {
  private menu: Menu | null = null;
  private listener: MenuManagerListener | null = null;
  private readonly separator: MenuItemConstructorOptions = { type: 'separator' };
  private isPremium: boolean = false;

  constructor(
    private readonly logger: LogService,
    private readonly settings: SettingsManager,
    private readonly config: AppConfig,
  ) {
  }

  initialize(listener: MenuManagerListener): void {
    this.listener = listener;
    this.updateMenu();
  }

  cleanup(): void {
    this.menu?.removeAllListeners();
    this.menu = null;
    this.listener = null;
  }

  updatePremiumStatus(isPremium: boolean): void {
    this.isPremium = isPremium;
    this.updateMenu();
  }

  private updateMenu(): void {
    this.menu = Menu.buildFromTemplate(this.getMenuTemplate());
    Menu.setApplicationMenu(this.menu);
  }

  private openLink(url: string): void {
    shell.openExternal(url).catch(error => this.logger.error(error));
  }

  private openPath(path: string): void {
    shell.openPath(path).catch(error => this.logger.error(error));
  }

  private getMenuTemplate(): MenuItemConstructorOptions[] {
    const macAppMenu: MenuItemConstructorOptions = {
      label: app.name,
      submenu: [
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        this.separator,
        { role: 'quit' },
      ],
    };
    return [
      ...(this.config.isMac ? [macAppMenu] : []),
      this.getFileMenu(),
      this.getEditMenu(),
      this.getViewMenu(),
      this.getHelpMenu(),
      ...(this.config.isDev ? [this.getDebugMenu()] : []),
      // Re-render the menu with the 'Get rotki Premium' button if the user who just logged in
      // is not a premium user, otherwise render the menu without the button. Since we are unable to just toggle
      // visibility on a top-level menu item, we instead have to add/remove it from the menu upon every login
      // (see https://github.com/electron/electron/issues/8703).
      ...(!this.isPremium ? [this.getPremiumMenu()] : []),
    ];
  }

  private getHelpMenu(): MenuItemConstructorOptions {
    return {
      label: '&Help',
      submenu: [
        {
          label: 'Usage Guide',
          click: () => this.openLink(externalLinks.usageGuide),
        },
        {
          label: 'Frequently Asked Questions',
          click: () => this.openLink(externalLinks.faq),
        },
        this.separator,
        {
          label: 'Release Notes',
          click: () => this.openLink(externalLinks.changeLog),
        },
        this.separator,
        {
          label: 'Issue / Feature Requests',
          click: () => this.openLink(externalLinks.githubIssues),
        },
        {
          label: 'Logs Directory',
          click: () => this.openPath(app.getPath('logs')),
        },
        this.separator,
        {
          label: 'Clear Cache',
          click: (_item: MenuItem, window?: BaseWindow) => {
            if (!window || !(window instanceof BrowserWindow)) {
              console.warn('window is not a BrowserWindow');
              return;
            }

            this.logger.debug('clearing cache');
            window.webContents.session.clearCache()
              .then(() => window.webContents.reloadIgnoringCache())
              .catch(error => this.logger.error(error));
          },
        },
        {
          label: 'Reset Settings / Restart Backend',
          click: (_item: MenuItem, window?: BaseWindow) => {
            if (!window || !(window instanceof BrowserWindow)) {
              console.warn('window is not a BrowserWindow');
              return;
            }

            window.webContents.session.clearStorageData().then(() => {
              window.webContents.send(IpcCommands.REQUEST_RESTART);
            }).catch(error => this.logger.error(error));
          },
        },
        this.separator,
        {
          label: 'About',
          click: (_item: MenuItem, window?: BaseWindow) => {
            if (!window || !(window instanceof BrowserWindow)) {
              console.warn('window is not a BrowserWindow');
              return;
            }

            window.webContents.send(IpcCommands.ABOUT);
          },
        },
      ],
    };
  }

  private getDebugMenu(): MenuItemConstructorOptions {
    return {
      label: '&Debug',
      submenu: [{
        label: 'Persist store',
        type: 'checkbox',
        checked: this.settings.appSettings.persistStore ?? false,
        click: (item: MenuItem, window?: BaseWindow) => {
          if (!window || !(window instanceof BrowserWindow)) {
            console.warn('window is not a BrowserWindow');
            return;
          }

          const enabled = item.checked;
          this.settings.appSettings.persistStore = enabled;
          this.settings.save();
          window.webContents.send(IpcCommands.DEBUG_SETTINGS, { persistStore: enabled });
          window.reload();
        },
      }],
    };
  }

  private getPremiumMenu(): MenuItemConstructorOptions {
    return {
      label: '&Get rotki Premium',
      ...(this.config.isMac
        ? {
          // submenu is mandatory to be displayed on macOS
            submenu: [
              {
                label: 'Get rotki Premium',
                id: 'premium-button',
                click: () => this.openLink(externalLinks.premium),
              },
            ],
          }
        : {
            id: 'premium-button',
            click: () => this.openLink(externalLinks.premium),
          }),
    };
  }

  private getEditMenu(): MenuItemConstructorOptions {
    const macEditOptions: MenuItemConstructorOptions[] = [
      { role: 'pasteAndMatchStyle' },
      { role: 'delete' },
      { role: 'selectAll' },
      this.separator,
      {
        label: 'Speech',
        submenu: [{ role: 'startSpeaking' }, { role: 'stopSpeaking' }],
      },
    ];

    const editOptions: MenuItemConstructorOptions[] = [
      { role: 'delete' },
      this.separator,
      { role: 'selectAll' },
    ];

    return {
      label: '&Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        this.separator,
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
        // Macs have special copy/paste and speech functionality
        ...(this.config.isMac ? macEditOptions : editOptions),
      ],
    };
  }

  private getFileMenu(): MenuItemConstructorOptions {
    return {
      label: 'File',
      submenu: [this.config.isMac ? { role: 'close' } : { role: 'quit' }],
    };
  }

  private getViewMenu(): MenuItemConstructorOptions {
    const minimize: MenuItemConstructorOptions = {
      id: 'MINIMIZE_TO_TRAY',
      label: 'Minimize to tray',
      enabled: this.settings.appSettings.displayTray,
      click: (_: MenuItem, window?: BaseWindow) => {
        window?.hide();
      },
    };

    const developmentDevTools: MenuItemConstructorOptions[] = [
      { role: 'reload' },
      { role: 'forceReload' },
      { role: 'toggleDevTools' },
      this.separator,
    ];

    const productionDevTools: MenuItemConstructorOptions[] = [
      { role: 'toggleDevTools', visible: false },
    ];

    const displayTrayIcon: MenuItemConstructorOptions = {
      label: 'Display Tray Icon',
      type: 'checkbox',
      checked: this.settings.appSettings.displayTray,
      click: (item: MenuItem) => {
        const displayTray = item.checked;
        this.settings.appSettings.displayTray = displayTray;
        this.settings.save();

        const applicationMenu = Menu.getApplicationMenu();
        if (applicationMenu) {
          const menuItem = applicationMenu.getMenuItemById('MINIMIZE_TO_TRAY');
          if (menuItem)
            menuItem.enabled = displayTray;
        }

        const listener = this.listener;
        assert(listener);
        listener.onDisplayTrayChanged(displayTray);
      },
    };

    return {
      label: '&View',
      submenu: [
        ...(this.config.isDev ? developmentDevTools : productionDevTools),
        { role: 'minimize' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        this.separator,
        { role: 'togglefullscreen' },
        minimize,
        this.separator,
        displayTrayIcon,
      ],
    };
  }
}
