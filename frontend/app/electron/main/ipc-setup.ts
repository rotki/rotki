import type { AppConfig } from '@electron/main/app-config';
import type { LogService } from '@electron/main/log-service';
import type { SettingsManager } from '@electron/main/settings-manager';
import type { BackendOptions, Credentials, McpServerStatus, TrayUpdate } from '@shared/ipc';
import type { LogLevel } from '@shared/log-level';
import { IpcCommands } from '@electron/ipc-commands';
import {
  BackendHandlers,
  OAuthHandlers,
  SecurityHandlers,
  SystemHandlers,
  UpdateHandlers,
  WalletBridgeIpcHandlers,
  WalletImportHandlers,
} from '@electron/main/ipc-handlers';
import { WalletBridgeHandlers } from '@electron/main/wallet-bridge-handlers';
import { WalletBridgeWebSocketServer } from '@electron/main/ws';
import { startPromise } from '@shared/utils';
import { ipcMain } from 'electron';

interface Callbacks {
  quit: () => Promise<void>;
  updateTray: (trayUpdate: TrayUpdate) => void;
  updatePremiumMenu: (isPremium: boolean) => void;
  restartSubprocesses: (options: Partial<BackendOptions>) => Promise<void>;
  terminateSubprocesses: (update?: boolean) => Promise<void>;
  updateDownloadProgress: (progress: number) => void;
  getProtocolRegistrationFailed: () => boolean;
  openOAuthInWindow: (url: string) => Promise<void>;
  sendIpcMessage: (channel: string, ...args: any[]) => void;
  getMcpServerStatus: () => Promise<McpServerStatus>;
  setMcpAutoStart: (enabled: boolean) => Promise<McpServerStatus>;
  startMcpServer: () => Promise<McpServerStatus>;
  stopMcpServer: () => Promise<McpServerStatus>;
  resetMcpSession: () => Promise<void>;
}

export class IpcManager {
  private readonly walletBridgeWebSocketServer: WalletBridgeWebSocketServer;
  private readonly walletBridgeHandlers: WalletBridgeHandlers;
  private readonly systemHandlers: SystemHandlers;
  private readonly backendHandlers: BackendHandlers;
  private readonly updateHandlers: UpdateHandlers;
  private readonly securityHandlers: SecurityHandlers;
  private readonly walletImportHandlers: WalletImportHandlers;
  private readonly walletBridgeIpcHandlers: WalletBridgeIpcHandlers;
  private readonly oauthHandlers: OAuthHandlers;

  private callbacks: Callbacks | null = null;
  private readonly registeredListeners: string[] = [];
  private readonly registeredHandlers: string[] = [];

  private get requireCallbacks(): Callbacks {
    const callbacks = this.callbacks;
    if (!callbacks) {
      throw new Error('IpcManager callbacks not initialized');
    }
    return callbacks;
  }

  constructor(
    private readonly logger: LogService,
    private readonly settings: SettingsManager,
    private readonly config: AppConfig,
  ) {
    this.walletBridgeWebSocketServer = new WalletBridgeWebSocketServer(logger);
    this.walletBridgeHandlers = new WalletBridgeHandlers(logger, this.walletBridgeWebSocketServer);

    // Initialize handler classes
    this.systemHandlers = new SystemHandlers(logger, settings, config);
    this.backendHandlers = new BackendHandlers(logger);
    this.updateHandlers = new UpdateHandlers(logger, config);
    this.securityHandlers = new SecurityHandlers();
    this.walletImportHandlers = new WalletImportHandlers(logger);
    this.walletBridgeIpcHandlers = new WalletBridgeIpcHandlers(logger, this.walletBridgeWebSocketServer);
    this.oauthHandlers = new OAuthHandlers(logger);

    // Set up bridge disconnection callback
    this.walletBridgeWebSocketServer.setOnBridgeDisconnected(() => {
      this.handleBridgeDisconnected();
    });

    // Set up bridge reconnection callback
    this.walletBridgeWebSocketServer.setOnBridgeReconnected(() => {
      this.handleBridgeReconnected();
    });
  }

  /**
   * Registers an `ipcMain` listener and records its channel so `cleanup()` can
   * remove it again. Registering through here rather than touching `ipcMain`
   * directly is what keeps teardown complete as handlers get added over time.
   */
  private on(channel: string, listener: Parameters<typeof ipcMain.on>[1]): void {
    this.registeredListeners.push(channel);
    ipcMain.on(channel, listener);
  }

  /**
   * Registers an `ipcMain` invoke handler, recorded for `cleanup()` the same way
   * as {@link on}. Handlers need `removeHandler`, not `removeAllListeners`.
   */
  private handle(channel: string, listener: Parameters<typeof ipcMain.handle>[1]): void {
    this.registeredHandlers.push(channel);
    ipcMain.handle(channel, listener);
  }

  initialize(callbacks: Callbacks) {
    this.callbacks = callbacks;
    this.logger.info('Registering IPC handlers');

    // Initialize handler classes with their callbacks
    this.systemHandlers.initialize({
      updateTray: callbacks.updateTray,
      getProtocolRegistrationFailed: callbacks.getProtocolRegistrationFailed,
      openOAuthInWindow: callbacks.openOAuthInWindow,
    });

    this.backendHandlers.initialize({
      restartSubprocesses: callbacks.restartSubprocesses,
      sendIpcMessage: callbacks.sendIpcMessage,
    });

    this.updateHandlers.initialize({
      terminateSubprocesses: callbacks.terminateSubprocesses,
      updateDownloadProgress: callbacks.updateDownloadProgress,
    });

    this.walletBridgeIpcHandlers.initialize({
      sendIpcMessage: callbacks.sendIpcMessage,
    });

    // System handlers
    this.on(IpcCommands.SYNC_GET_DEBUG, (event) => {
      event.returnValue = this.systemHandlers.getDebugSettings();
    });
    this.on(IpcCommands.SYNC_API_URL, (event) => {
      event.returnValue = this.systemHandlers.getApiUrls();
    });
    this.on(IpcCommands.PREMIUM_LOGIN, (_event, showPremium) => {
      callbacks.updatePremiumMenu(showPremium);
    });
    this.handle(IpcCommands.INVOKE_CLOSE_APP, callbacks.quit);
    this.handle(IpcCommands.INVOKE_OPEN_URL, async (_, url: string) => this.systemHandlers.openUrl(url));
    this.handle(IpcCommands.INVOKE_OPEN_DIRECTORY, async (_, title: string, defaultPath?: string) => this.systemHandlers.openDirectory(title, defaultPath));
    this.handle(IpcCommands.INVOKE_OPEN_PATH, (_, path: string) => this.systemHandlers.openPath(path));
    this.handle(IpcCommands.INVOKE_CONFIG, async (_, defaultConfig: boolean) => this.systemHandlers.getConfig(defaultConfig));
    this.handle(IpcCommands.INVOKE_VERSION, () => this.systemHandlers.getVersion());
    this.handle(IpcCommands.INVOKE_IS_MAC, () => this.systemHandlers.getIsMac());
    this.handle(IpcCommands.INVOKE_THEME, (_, selectedTheme: number) => this.systemHandlers.setSelectedTheme(selectedTheme));
    this.on(IpcCommands.LOG_TO_FILE, (_, level: LogLevel, message: string) => {
      this.systemHandlers.logToFile(level, message);
    });
    this.on(IpcCommands.SET_LOG_LEVEL, (_, level: LogLevel) => {
      this.systemHandlers.setLogLevel(level);
    });
    this.on(IpcCommands.TRAY_UPDATE, (_event, trayUpdate: TrayUpdate) => {
      this.systemHandlers.updateTray(trayUpdate);
    });

    // Backend handlers
    this.handle(IpcCommands.INVOKE_SUBPROCESS_START, async (_event, options) => this.backendHandlers.restartBackend(options));

    // Update handlers
    this.handle(IpcCommands.INVOKE_UPDATE_CHECK, this.updateHandlers.checkForUpdates);
    this.handle(IpcCommands.INVOKE_DOWNLOAD_UPDATE, this.updateHandlers.downloadUpdate);
    this.handle(IpcCommands.INVOKE_INSTALL_UPDATE, this.updateHandlers.installUpdate);

    // Security handlers
    this.handle(IpcCommands.INVOKE_STORE_PASSWORD, async (_, credentials: Credentials) => this.securityHandlers.storePassword(credentials));
    this.handle(IpcCommands.INVOKE_GET_PASSWORD, async (_, username: string) => this.securityHandlers.getPassword(username));
    this.handle(IpcCommands.INVOKE_CLEAR_PASSWORD, async () => this.securityHandlers.clearPassword());
    this.handle(IpcCommands.INVOKE_MCP_STATUS, callbacks.getMcpServerStatus);
    this.handle(IpcCommands.INVOKE_MCP_AUTOSTART, async (_event, enabled: boolean) => callbacks.setMcpAutoStart(enabled));
    this.handle(IpcCommands.INVOKE_MCP_START, callbacks.startMcpServer);
    this.handle(IpcCommands.INVOKE_MCP_STOP, callbacks.stopMcpServer);
    this.handle(IpcCommands.INVOKE_MCP_RESET_SESSION, callbacks.resetMcpSession);

    // Wallet import handlers
    this.handle(IpcCommands.INVOKE_WALLET_IMPORT, this.walletImportHandlers.importFromWallet);

    // Wallet bridge IPC handlers
    this.handle(IpcCommands.OPEN_WALLET_CONNECT_BRIDGE, this.walletBridgeIpcHandlers.openWalletConnectBridge);
    this.handle(IpcCommands.WALLET_BRIDGE_HTTP_LISTENING, this.walletBridgeIpcHandlers.handleWalletBridgeHttpListening);
    this.handle(IpcCommands.WALLET_BRIDGE_WS_LISTENING, this.walletBridgeIpcHandlers.handleWalletBridgeWsListening);
    this.handle(IpcCommands.WALLET_BRIDGE_CLIENT_READY, this.walletBridgeIpcHandlers.handleWalletBridgeClientReady);
    this.on(IpcCommands.USER_LOGOUT, () => {
      this.walletBridgeIpcHandlers.handleUserLogout();
      startPromise(this.oauthHandlers.clearOAuthCookies());
    });

    // Wallet Bridge handlers (from existing handler class)
    this.handle(IpcCommands.WALLET_BRIDGE_REQUEST, this.walletBridgeHandlers.handleWalletBridgeRequest);
    this.handle(IpcCommands.WALLET_BRIDGE_IS_CLIENT_CONNECTED, this.walletBridgeHandlers.handleWalletBridgeConnectionStatus);
    this.handle(IpcCommands.WALLET_BRIDGE_STOP_SERVERS, this.walletBridgeIpcHandlers.handleStopServers);

    // EIP-6963 Provider Detection handlers
    this.handle(IpcCommands.WALLET_BRIDGE_GET_PROVIDERS, this.walletBridgeIpcHandlers.getAvailableProviders);
    this.handle(IpcCommands.WALLET_BRIDGE_SELECT_PROVIDER, this.walletBridgeIpcHandlers.selectProvider);
    this.handle(IpcCommands.WALLET_BRIDGE_GET_SELECTED_PROVIDER, this.walletBridgeIpcHandlers.getSelectedProvider);
  }

  /**
   * Clears OAuth cookies on app startup to ensure clean state.
   * This handles cases where the previous user didn't properly log out.
   */
  clearOAuthCookiesOnStartup(): void {
    startPromise(this.oauthHandlers.clearOAuthCookies('startup'));
  }

  async cleanup(): Promise<void> {
    this.logger.info('Cleaning up IPC manager resources...');

    // Drop every registered handler. They close over this manager and its
    // handler classes, and a live handler can keep the process from exiting.
    for (const channel of this.registeredListeners)
      ipcMain.removeAllListeners(channel);

    for (const channel of this.registeredHandlers)
      ipcMain.removeHandler(channel);

    this.registeredListeners.length = 0;
    this.registeredHandlers.length = 0;
    this.callbacks = null;

    // Stop WebSocket server, waiting for it to release its handle
    await this.walletBridgeWebSocketServer.stop();

    // Cleanup wallet import handlers (they manage their own servers)
    this.walletImportHandlers.cleanup();
  }

  private readonly handleBridgeDisconnected = (): void => {
    // Notify the main window that the bridge has been disconnected
    this.logger.info('Bridge disconnected, sending notification to main window');
    this.requireCallbacks.sendIpcMessage(IpcCommands.WALLET_BRIDGE_CONNECTION_STATUS, 'disconnected');
  };

  private readonly handleBridgeReconnected = (): void => {
    // Notify the main window that the bridge has been reconnected
    this.logger.info('Bridge reconnected, sending notification to main window');
    this.requireCallbacks.sendIpcMessage(IpcCommands.WALLET_BRIDGE_CONNECTION_STATUS, 'reconnected');
  };
}
