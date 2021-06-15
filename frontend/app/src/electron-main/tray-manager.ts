import path from 'path';
import { app, BrowserWindow, Menu, Tray } from 'electron';
import { TrayUpdate } from '@/electron-main/ipc';
import { Nullable } from '@/types';

type WindowProvider = () => BrowserWindow;
const isMac = process.platform === 'darwin';

export class TrayManager {
  private readonly getWindow: WindowProvider;
  private readonly closeApp: () => void;
  private tray: Nullable<Tray> = null;

  constructor(getWindow: WindowProvider, closeApp: () => void) {
    this.getWindow = getWindow;
    this.closeApp = closeApp;
    this.build();
  }

  private static get iconPath(): string {
    return process.env.NODE_ENV !== 'production'
      ? path.join(__dirname, '..', 'public')
      : __dirname;
  }

  private buildMenu(visible: boolean, showHide: () => void) {
    return Menu.buildFromTemplate([
      {
        label: 'rotki',
        icon: path.join(TrayManager.iconPath, 'rotki_tray.png')
      },
      { type: 'separator' },
      {
        label: visible ? 'Minimize to tray' : 'Restore from tray',
        click: showHide
      },
      { type: 'separator' },
      {
        label: 'Quit',
        click: this.closeApp
      }
    ]);
  }

  update({ currency, delta, percentage, up, period, netWorth }: TrayUpdate) {
    if (up === undefined) {
      this.setIcon(isMac ? 'rotki-trayTemplate.png' : 'rotki_tray.png');
      this.tray?.setTitle('');
      this.tray?.setToolTip('rotki is running');
      return;
    }

    let indicator: string;
    let color: string;
    let icon: string;
    if (up) {
      icon = 'rotki_up.png';
      color = '\x1b[32m';
      indicator = '▲';
    } else {
      icon = 'rotki_down.png';
      color = '\x1b[31m';
      indicator = '▼';
    }

    if (!isMac) {
      this.setIcon(icon);
    }

    this.tray?.setTitle(color + indicator);
    this.tray?.setToolTip(
      `rotki: ${netWorth} ${currency}.\nChange in ${period} period ${indicator} ${percentage}%\n(${delta} ${currency})`
    );
  }

  private setIcon(iconName: string) {
    const iconPath = path.join(TrayManager.iconPath, iconName);
    this.tray?.setImage(iconPath);
  }

  build() {
    const iconPath = path.join(TrayManager.iconPath, 'rotki-trayTemplate.png');
    this.tray = new Tray(iconPath);
    this.tray.setToolTip('rotki is running');

    const showHide = () => {
      const win = this.getWindow();
      if (win.isVisible()) {
        win.hide();
      } else {
        win.show();
        app.focus();
      }

      this.tray?.setContextMenu(this.buildMenu(win.isVisible(), showHide));
    };

    this.tray.setContextMenu(this.buildMenu(true, showHide));
    this.tray.on('double-click', showHide);
    this.tray.on('click', showHide);
  }

  destroy() {
    this.tray?.destroy();
    this.tray = null;
  }
}
