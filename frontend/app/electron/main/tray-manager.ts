import path from 'node:path';
import process from 'node:process';
import { Menu, Tray, nativeImage } from 'electron';
import { checkIfDevelopment } from '@shared/utils';
import { assert } from '@rotki/common';
import type { SettingsManager } from '@electron/main/settings-manager';
import type { TrayUpdate } from '@shared/ipc';

const dirname = import.meta.dirname;

const isMac = process.platform === 'darwin';

interface TrayManagerListener {
  toggleWindowVisibility: () => boolean;
  quit: () => void;
}

export class TrayManager {
  private tooltip = '';
  private tray?: Tray;
  private listener?: TrayManagerListener;
  private isVisible = false;

  constructor(private readonly settings: SettingsManager) {

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
        click: () => this.toggleWindowVisibility(),
      },
      { type: 'separator' },
      {
        label: 'Quit',
        click: this.listener?.quit,
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

    this.updateContextMenu(this.isVisible);
  }

  private setIcon(iconName: string) {
    const iconPath = path.join(TrayManager.iconPath, iconName);
    const trayIcon = nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 });
    this.tray?.setImage(trayIcon);
  }

  private toggleWindowVisibility() {
    const listener = this.listener;
    assert(listener, 'No listener set');
    const visible = listener.toggleWindowVisibility();
    this.updateContextMenu(visible);
  }

  updateContextMenu(visible: boolean) {
    this.isVisible = visible;
    this.tray?.setContextMenu(this.buildMenu(visible, this.tooltip));
  }

  build() {
    const icon = isMac ? 'rotki-trayTemplate@5.png' : 'rotki_tray@5x.png';
    const iconPath = path.join(TrayManager.iconPath, icon);
    const trayIcon = nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 });
    this.tray = new Tray(trayIcon);
    this.tray.setToolTip('rotki is running');

    this.tray.setContextMenu(this.buildMenu(true));
    this.tray.on('double-click', () => this.toggleWindowVisibility());
    this.tray.on('click', () => this.toggleWindowVisibility());
  }

  cleanup() {
    if (this.tray) {
      this.tray.destroy();
      this.tray = undefined;
    }
    this.listener = undefined;
  }

  initialize(listener: TrayManagerListener) {
    if (!this.settings.appSettings.displayTray) {
      return;
    }

    this.build();
    this.listener = listener;
  }
}
