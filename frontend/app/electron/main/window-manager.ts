import type { LogService } from '@electron/main/log-service';
import type { BackendCode, OAuthResult, StartupError } from '@shared/ipc';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { IpcCommands } from '@electron/ipc-commands';
import { ContextMenuHandler } from '@electron/main/context-menu-handler';
import { createProtocol } from '@electron/main/create-protocol';
import { NavigationHandler } from '@electron/main/navigation-handler';
import { parseToken } from '@electron/main/oauth-utils';
import { WindowConfig } from '@electron/main/window-config';
import { assert } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { BrowserWindow, ipcMain } from 'electron';
import windowStateKeeper from 'electron-window-state';

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

  // Startup error state management
  private startupError: StartupError | null = null;
  private rendererReady: boolean = false;

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
    this.setupStartupErrorHandlers();

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
      // Load extensions before the page to avoid interfering with dynamic imports
      await this.loadDevExtensions(window);
      // Load the url of the dev server if in development mode with retry logic
      await this.loadUrlWithRetry(window, devServerUrl);
      if (process.env.ENABLE_DEV_TOOLS)
        window.webContents.openDevTools();
      return;
    }

    createProtocol('app');
    // Load the index.html when not in development
    await window.loadURL('app://localhost/index.html');
  }

  private async loadDevExtensions(window: BrowserWindow): Promise<void> {
    // Path from dist/ to tools/chrome-task-tracker
    // import.meta.dirname points to dist/ in dev mode
    const extensionPath = path.resolve(import.meta.dirname, '..', '..', '..', 'tools', 'chrome-task-tracker');

    // Check if the extension directory exists
    if (!fs.existsSync(extensionPath)) {
      this.logger.debug(`Task tracker extension not found at: ${extensionPath}`);
      return;
    }

    try {
      const extension = await window.webContents.session.extensions.loadExtension(extensionPath, {
        allowFileAccess: true,
      });
      this.logger.info(`Loaded dev extension: ${extension.name} from ${extensionPath}`);
    }
    catch (error) {
      this.logger.warn('Failed to load task tracker extension:', error);
    }
  }

  private async loadUrlWithRetry(window: BrowserWindow, url: string, maxRetries: number = 5): Promise<void> {
    let lastError: Error | null = null;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        this.logger.debug(`Loading URL attempt ${attempt}/${maxRetries}: ${url}`);
        await window.loadURL(url);
        this.logger.debug(`Successfully loaded URL on attempt ${attempt}`);
        return;
      }
      catch (error) {
        lastError = error as Error;
        this.logger.warn(`Failed to load URL on attempt ${attempt}/${maxRetries}:`, error);

        // Don't retry on the last attempt
        if (attempt === maxRetries) {
          break;
        }

        // Wait with exponential backoff: 1s, 2s, 4s, 8s
        const delay = Math.min(1000 * (2 ** (attempt - 1)), 8000);
        this.logger.debug(`Retrying in ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }

    this.logger.error(`Failed to load URL after ${maxRetries} attempts. Last error:`, lastError);
    throw new Error(`Failed to load dev server URL after ${maxRetries} attempts: ${lastError?.message || 'Unknown error'}`);
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
    // Remove startup error IPC handlers
    ipcMain.removeAllListeners(IpcCommands.SYNC_GET_STARTUP_ERROR);
    ipcMain.removeAllListeners(IpcCommands.RENDERER_READY);
    // Reset startup error state
    this.startupError = null;
    this.rendererReady = false;
    // Clean up window listeners
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

  /**
   * Sets up IPC handlers for startup error management.
   * - SYNC_GET_STARTUP_ERROR: Synchronous handler for renderer to fetch current error state
   * - RENDERER_READY: Signal from renderer that it's ready to receive async messages
   */
  private setupStartupErrorHandlers(): void {
    // Sync handler - renderer fetches on init to get any error that occurred before ready
    ipcMain.on(IpcCommands.SYNC_GET_STARTUP_ERROR, (event) => {
      event.returnValue = this.startupError;
    });

    // Ready signal handler - renderer is now listening for async messages
    ipcMain.on(IpcCommands.RENDERER_READY, () => {
      this.onRendererReady();
    });
  }

  /**
   * Called when renderer signals it's ready to receive async messages.
   * If an error occurred before ready, push it now.
   */
  private onRendererReady(): void {
    this.rendererReady = true;
    // Push any error that occurred before renderer was ready
    if (this.startupError) {
      this.pushStartupError();
    }
  }

  /**
   * Push the current startup error to the renderer via async IPC.
   */
  private pushStartupError(): void {
    if (this.startupError && this.window?.webContents) {
      try {
        this.window.webContents.send(IpcCommands.STARTUP_ERROR, this.startupError);
      }
      catch (error) {
        this.logger.error('Failed to push startup error to renderer:', error);
      }
    }
  }

  /**
   * Store a startup error and notify the renderer.
   * If the renderer is already ready, push immediately via async IPC.
   * If not ready, the error will be fetched synchronously when the renderer initializes.
   */
  setStartupError(
    backendOutput: string | Error,
    code: BackendCode,
  ): void {
    const message = typeof backendOutput === 'string' ? backendOutput : backendOutput.message;
    this.startupError = { message, code };

    // If renderer is already ready, push immediately
    if (this.rendererReady) {
      this.pushStartupError();
    }
  }

  sendOAuthCallback(oAuthResult: OAuthResult): void {
    try {
      if (this.window?.webContents) {
        this.window.webContents.send('oauth-callback', oAuthResult);
      }
    }
    catch (error) {
      this.logger.error('Failed to send OAuth callback:', error);
    }
  }

  sendIpcMessage(channel: string, ...args: any[]): void {
    try {
      if (this.window?.webContents) {
        this.window.webContents.send(channel, ...args);
      }
    }
    catch (error) {
      this.logger.error(`Failed to send IPC message to channel ${channel}:`, error);
    }
  }

  async openOAuthWindow(url: string): Promise<void> {
    try {
      const oauthWindow = new BrowserWindow({
        width: 800,
        height: 800,
        show: false,
        autoHideMenuBar: true,
        webPreferences: {
          nodeIntegration: false,
          contextIsolation: true,
          sandbox: true,
        },
      });

      // Function to inject URL display
      const injectUrlDisplay = async () => {
        try {
          await oauthWindow.webContents.executeJavaScript(`
            const urlDisplay = document.createElement('input');
            urlDisplay.value = window.location.href;
            urlDisplay.readOnly = true;
            urlDisplay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:30px;z-index:10000;border:none;background:#f5f5f5;padding:5px;font-family:monospace;font-size:12px;box-sizing:border-box;';
            document.body.style.paddingTop = '30px';
            document.body.insertBefore(urlDisplay, document.body.firstChild);
          `);
        }
        catch (error) {
          this.logger.debug('Failed to inject URL display:', error);
        }
      };

      await oauthWindow.loadURL(url);
      await injectUrlDisplay();

      // Re-inject URL display after each navigation
      oauthWindow.webContents.on('did-finish-load', () => {
        startPromise(injectUrlDisplay());
      });

      oauthWindow.show();

      // Listen for navigation to detect OAuth callback
      oauthWindow.webContents.on('will-navigate', (event, navigationUrl) => {
        if (navigationUrl.startsWith('rotki://oauth/')) {
          event.preventDefault();
          this.sendOAuthCallback(parseToken(navigationUrl));
          oauthWindow.close();
        }
      });

      // Handle window close
      oauthWindow.on('closed', () => {
        this.logger.debug('OAuth window closed');
      });
    }
    catch (error) {
      this.logger.error('Failed to open OAuth window:', error);
    }
  }
}
