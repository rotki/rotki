import { type BrowserWindow, Menu, MenuItem } from 'electron';

export class ContextMenuHandler {
  setupContextMenu(window: BrowserWindow) {
    window.webContents.on('context-menu', (_event, props) => {
      const menu = this.createContextMenu(props);
      menu.popup({ window });
    });
  }

  private createContextMenu(props: Electron.ContextMenuParams): Menu {
    const menu = new Menu();
    this.addMenuItem(menu, props.editFlags.canCut, { label: 'Cut', role: 'cut' });
    this.addMenuItem(menu, props.editFlags.canCopy, { label: 'Copy', role: 'copy' });
    this.addMenuItem(menu, props.editFlags.canPaste, { label: 'Paste', role: 'paste' });
    return menu;
  }

  private addMenuItem(menu: Menu, condition: boolean, options: Electron.MenuItemConstructorOptions) {
    if (condition) {
      menu.append(new MenuItem(options));
    }
  }
}
