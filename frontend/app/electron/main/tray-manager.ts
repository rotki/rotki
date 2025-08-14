import type { AppConfig } from '@electron/main/app-config';
import type { SettingsManager } from '@electron/main/settings-manager';
import type { TrayUpdate } from '@shared/ipc';
import path from 'node:path';
import { assert } from '@rotki/common';
import { isDefined } from '@vueuse/core';
import { Menu, type MenuItem, type MenuItemConstructorOptions, nativeImage, Tray } from 'electron';

interface TrayManagerListener {
  toggleWindowVisibility: () => boolean;
  quit: () => void;
}

export class TrayManager {
  private tooltip = '';
  private tray?: Tray;
  private listener?: TrayManagerListener;
  private isVisible = false;
  private trayData?: TrayUpdate;

  constructor(private readonly settings: SettingsManager, private readonly config: AppConfig) {

  }

  private get iconPath(): string {
    return this.config.isDev ? path.join(import.meta.dirname, '..', 'public') : import.meta.dirname;
  }

  private buildMenu(visible: boolean, info = ''): Menu {
    return Menu.buildFromTemplate([
      {
        label: 'rotki',
        enabled: false,
        icon: path.join(this.iconPath, 'rotki_tray.png'),
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
      ...(this.config.isMac
        ? ([{
            label: 'Display net worth on the tray',
            type: 'checkbox',
            checked: this.settings.appSettings.showNetWorthOnTray,
            click: (item: MenuItem) => {
              const showNetWorthOnTray = item.checked;
              this.settings.appSettings.showNetWorthOnTray = showNetWorthOnTray;
              this.settings.save();

              this.update();
            },
          }] satisfies MenuItemConstructorOptions[])
        : []),
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

  update(tray?: TrayUpdate) {
    if (!this.tray)
      return;

    const trayData = tray ?? this.trayData;

    if (!trayData)
      return;

    const { currency, delta, percentage, up, period, netWorth } = trayData;
    this.trayData = trayData;

    let indicator: string;
    const tooltip: string[] = [];
    let color: string;
    let icon: string = 'rotki_tray@5x.png';
    let title: string = '';

    if (typeof up !== 'undefined') {
      if (up) {
        icon = 'rotki_up.png';
        color = '\u001B[32m';
        indicator = '▴';
      }
      else {
        icon = 'rotki_down.png';
        color = '\u001B[31m';
        indicator = '▾';
      }

      title += `${color}${indicator}\u001B[0m`;
      tooltip.push(`Change in ${period} period ${indicator} ${percentage}%\n(${delta} ${currency})`);
    }

    if (this.config.isMac)
      icon = 'rotki-trayTemplate@5x.png';

    if (this.settings.appSettings.showNetWorthOnTray) {
      if (isDefined(netWorth)) {
        title += ` ${netWorth} ${currency}`;
        tooltip.unshift(`Net worth ${netWorth} ${currency}.`);
      }
      else {
        title += ' rotki is running';
      }
    }

    this.setIcon(icon);
    this.tooltip = tooltip.length > 0 ? tooltip.join('\n') : 'rotki is running';
    this.tray.setToolTip(this.tooltip);
    this.tray.setTitle(title);
    this.updateContextMenu(this.isVisible);
  }

  private setIcon(iconName: string) {
    const iconPath = path.join(this.iconPath, iconName);
    const trayIcon = nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 });
    trayIcon.setTemplateImage(this.config.isMac);
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
    const icon = this.config.isMac ? 'rotki-trayTemplate@5x.png' : 'rotki_tray@5x.png';
    const iconPath = path.join(this.iconPath, icon);
    const trayIcon = nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 });
    trayIcon.setTemplateImage(this.config.isMac);
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
