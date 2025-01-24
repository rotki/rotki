import process from 'node:process';
import { NavigationHandler } from '@electron/main/navigation-handler';
import { ContextMenuHandler } from '@electron/main/context-menu-handler';
import windowStateKeeper from 'electron-window-state';
import { BrowserWindow, ipcMain } from 'electron';
import { createProtocol } from '@electron/main/create-protocol';
import { assert } from '@rotki/common';
import { WindowConfig } from '@electron/main/window-config';
import type { BackendCode } from '@shared/ipc';
import type { LogService } from '@electron/main/log-service';

interface WindowManagerListener {
  onWindowVisibilityChanged: (isVisible: boolean) => void;
  quit: () => void;
}

export class WindowManager {
  private window: BrowserWindow | null = null;
  private readonly navigation: NavigationHandler;
  private readonly contextMenuHandler: ContextMenuHandler;
  private readonly windowConfig: WindowConfig;

  private readonly isMac = process.platform === 'darwin';
  private forceQuit: boolean = false;
  private notificationInterval?: number;

  private listener: WindowManagerListener | null = null;

  private get requireWindow(): BrowserWindow {
    const window = this.window;
    assert(window);
    return window;
  }

  private get requireListener(): WindowManagerListener {
    const listener = this.listener;
    assert(listener);
    return listener;
  }

  constructor(private readonly logger: LogService) {
    this.navigation = new NavigationHandler();
    this.contextMenuHandler = new ContextMenuHandler();
    this.windowConfig = new WindowConfig();
  }

  async create(): Promise<BrowserWindow> {
    const windowState = this.createWindowState();
    this.window = new BrowserWindow(this.windowConfig.getWindowOptions(windowState));

    windowState.manage(this.window);

    await this.loadContent(this.window);

    this.setupEventListeners(this.window);
    this.navigation.setupNavigationEvents(this.window.webContents);
    this.contextMenuHandler.setupContextMenu(this.window);
    this.listenForAckMessages();

    return this.window;
  }

  setListener(listener: WindowManagerListener) {
    this.listener = listener;
    this.requireWindow.on('show', () => this.requireListener.onWindowVisibilityChanged(true));
    this.requireWindow.on('hide', () => this.requireListener.onWindowVisibilityChanged(true));
  };

  readonly focus = (): void => {
    const window = this.window;
    if (!window)
      return;

    if (window.isMinimized())
      window.restore();

    window.focus();
  };

  readonly forceClose = (): void => {
    this.forceQuit = true;
  };

  readonly activate = async (): Promise<void> => {
    // On macOS it's common to re-create a window in the app when the
    // dock icon is clicked and there are no other windows open.
    if (this.window === null)
      await this.create();
    else
      this.window.show();
  };

  readonly updateProgress = (progress: number): void => {
    this.window?.setProgressBar(progress);
  };

  private async loadContent(window: BrowserWindow): Promise<void> {
    const devServerUrl = import.meta.env.VITE_DEV_SERVER_URL;
    if (devServerUrl) {
      // Load the url of the dev server if in development mode
      await window.loadURL(devServerUrl);
      if (process.env.ENABLE_DEV_TOOLS)
        window.webContents.openDevTools();
      return;
    }

    createProtocol('app');
    // Load the index.html when not in development
    await window.loadURL('app://./index.html');
  }

  private createWindowState() {
    const screen = this.windowConfig.getScreenDimensions();
    return windowStateKeeper({
      defaultWidth: screen.defaultWidth,
      defaultHeight: screen.defaultHeight,
    });
  }

  private handleClose(event: Electron.Event): void {
    event.preventDefault();

    if (this.isMac && !this.forceQuit) {
      this.window?.hide();
      return;
    }

    this.requireListener.quit();
  }

  private handleClosed() {
    if (this.isMac && !this.forceQuit) {
      this.window?.hide();
    }
    else {
      this.window = null;
    }
  }

  toggleVisibility() {
    const window = this.window;
    assert(window);
    if (window.isVisible()) {
      window.hide();
    }
    else {
      window.show();
      window.focus();
    }
    return window.isVisible();
  }

  cleanup() {
    this.clearPending();
    this.window?.removeAllListeners('show');
    this.window?.removeAllListeners('hide');
    this.window?.removeAllListeners('close');
    this.window?.removeAllListeners('closed');
    this.listener = null;
    this.window = null;
  }

  private setupEventListeners(window: BrowserWindow) {
    window.on('close', e => this.handleClose(e));
    window.on('closed', () => this.handleClosed());
  }

  listenForAckMessages() {
    // Listen for ack messages from renderer process
    ipcMain.on('ack', (event, ...args) => {
      if (args[0] === 1)
        this.clearPending();
      else
        this.logger.log(`Warning: unknown ack code ${args[0]}`);
    });
  }

  private clearPending() {
    if (this.notificationInterval)
      clearInterval(this.notificationInterval);
  }

  notify(
    backendOutput: string | Error,
    code: BackendCode,
  ): void {
    this.clearPending();
    // Notify the main window every 2 seconds until it acks the notification
    this.notificationInterval = setInterval(() => {
      /**
       * There is a possibility that the window has been already disposed and this
       * will result in an exception. In that case, we just catch and clear the notifier
       */
      try {
        this.window?.webContents.send('failed', backendOutput, code);
      }
      catch {
        clearInterval(this.notificationInterval);
      }
    }, 2000) as unknown as number;
  }
}
