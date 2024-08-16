import path from 'node:path';
import process from 'node:process';
import { type BrowserWindow, Menu, Tray, app, nativeImage } from 'electron';
import { settingsManager } from '@electron/main/settings-manager';
import { checkIfDevelopment } from '@shared/utils';
import type { TrayUpdate } from '@shared/ipc';

const dirname = import.meta.dirname;

type WindowProvider = () => BrowserWindow;
const isMac = process.platform === 'darwin';

export class TrayManager {
  private readonly getWindow: WindowProvider;
  private readonly closeApp: () => void;
  private tooltip = '';
  private tray?: Tray = undefined;

  constructor(getWindow: WindowProvider, closeApp: () => void) {
    this.getWindow = getWindow;
    this.closeApp = closeApp;
    if (settingsManager.appSettings.displayTray)
      this.build();
  }

  private static get iconPath(): string {
    return checkIfDevelopment() ? path.join(dirname, '..', 'public') : dirname;
  }

  private buildMenu(visible: boolean, info = '') {
    return Menu.buildFromTemplate([
      {
        label: 'rotki',
        enabled: false,
        icon: path.join(TrayManager.iconPath, 'rotki_tray.png'),
      },
      ...(info
        ? [
            {
              label: info,
              enabled: false,
            },
          ]
        : []),
      { type: 'separator' },
      {
        label: visible ? 'Minimize to tray' : 'Restore from tray',
        click: () => this.showHide(this.getWindow()),
      },
      { type: 'separator' },
      {
        label: 'Quit',
        click: this.closeApp,
      },
    ]);
  }

  update({ currency, delta, percentage, up, period, netWorth }: TrayUpdate) {
    if (!this.tray)
      return;

    if (up === undefined) {
      this.setIcon(isMac ? 'rotki-trayTemplate@5.png' : 'rotki_tray@5x.png');
      this.tray.setTitle('');
      this.tray.setToolTip('rotki is running');
      return;
    }

    let indicator: string;
    let color: string;
    let icon: string;
    if (up) {
      icon = 'rotki_up.png';
      color = '\u001B[32m';
      indicator = '▲';
    }
    else {
      icon = 'rotki_down.png';
      color = '\u001B[31m';
      indicator = '▼';
    }

    if (!isMac)
      this.setIcon(icon);

    this.tray.setTitle(color + indicator);
    this.tooltip = `Net worth ${netWorth} ${currency}.\nChange in ${period} period ${indicator} ${percentage}%\n(${delta} ${currency})`;
    this.tray.setToolTip(this.tooltip);

    const visible = this.getWindow().isVisible();
    this.tray.setContextMenu(this.buildMenu(visible, this.tooltip));
  }

  private setIcon(iconName: string) {
    const iconPath = path.join(TrayManager.iconPath, iconName);
    const trayIcon = nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 });
    this.tray?.setImage(trayIcon);
  }

  private showHide(win: BrowserWindow) {
    if (win.isVisible()) {
      win.hide();
    }
    else {
      win.show();
      app.focus();
    }

    this.tray?.setContextMenu(this.buildMenu(win.isVisible()));
  }

  private hidden = () => {
    this.tray?.setContextMenu(this.buildMenu(false, this.tooltip));
  };

  private shown = () => {
    this.tray?.setContextMenu(this.buildMenu(true, this.tooltip));
  };

  build() {
    const icon = isMac ? 'rotki-trayTemplate@5.png' : 'rotki_tray@5x.png';
    const iconPath = path.join(TrayManager.iconPath, icon);
    const trayIcon = nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 });
    this.tray = new Tray(trayIcon);
    this.tray.setToolTip('rotki is running');

    this.tray.setContextMenu(this.buildMenu(true));
    this.tray.on('double-click', () => this.showHide(this.getWindow()));
    this.tray.on('click', () => this.showHide(this.getWindow()));
  }

  destroy() {
    if (this.tray) {
      this.tray.destroy();
      this.tray = undefined;
    }
  }

  listen() {
    const window = this.getWindow();
    window.on('hide', this.hidden);
    window.on('show', this.shown);
  }
}
