import path from 'path';
import { app, BrowserWindow, Menu, Tray } from 'electron';
import { TrayUpdate } from '@/electron-main/ipc';
import { Nullable } from '@/types';

type WindowProvider = () => BrowserWindow;

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
        icon: path.join(TrayManager.iconPath, 'favicon-16x16.png')
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

  update({ currency, delta, percentage, up, period }: TrayUpdate) {
    if (up === undefined) {
      this.setIcon('android-chrome-192x192.png');
      this.tray?.setToolTip('rotki is running');
      return;
    }

    let indicator: string;
    if (up) {
      this.setIcon('rotki_up-64x64.png');
      indicator = '▲';
    } else {
      this.setIcon('rotki_down-64x64.png');
      indicator = '▼';
    }

    this.tray?.setToolTip(
      `rotki: ${period} ${indicator} ${percentage}% (${delta} ${currency})`
    );
  }

  private setIcon(iconName: string) {
    const iconPath = path.join(TrayManager.iconPath, iconName);
    this.tray?.setImage(iconPath);
  }

  build() {
    const iconPath = path.join(
      TrayManager.iconPath,
      'android-chrome-192x192.png'
    );
    this.tray = new Tray(iconPath);
    this.tray.setTitle('rotki');
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
