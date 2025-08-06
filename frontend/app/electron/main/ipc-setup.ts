import type { AppConfig } from '@electron/main/app-config';
import type { LogService } from '@electron/main/log-service';
import type { SettingsManager } from '@electron/main/settings-manager';
import type { BackendOptions, Credentials, TrayUpdate } from '@shared/ipc';
import type { LogLevel } from '@shared/log-level';
import { IpcCommands } from '@electron/ipc-commands';
import {
  BackendHandlers,
  SecurityHandlers,
  SystemHandlers,
  UpdateHandlers,
  WalletBridgeIpcHandlers,
  WalletImportHandlers,
} from '@electron/main/ipc-handlers';
import { WalletBridgeHandlers } from '@electron/main/wallet-bridge-handlers';
import { WalletBridgeWebSocketServer } from '@electron/main/ws';
import { ipcMain } from 'electron';

interface Callbacks {
  quit: () => Promise<void>;
  updateTray: (trayUpdate: TrayUpdate) => void;
  updatePremiumMenu: (isPremium: boolean) => void;
  restartSubprocesses: (options: Partial<BackendOptions>) => Promise<void>;
  terminateSubprocesses: (update?: boolean) => Promise<void>;
  getRunningCorePIDs: () => Promise<number[]>;
  updateDownloadProgress: (progress: number) => void;
  getProtocolRegistrationFailed: () => boolean;
  openOAuthInWindow: (url: string) => Promise<void>;
  sendIpcMessage: (channel: string, ...args: any[]) => void;
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

  private callbacks: Callbacks | null = null;

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

    // Set up bridge disconnection callback
    this.walletBridgeWebSocketServer.setOnBridgeDisconnected(() => {
      this.handleBridgeDisconnected();
    });

    // Set up bridge reconnection callback
    this.walletBridgeWebSocketServer.setOnBridgeReconnected(() => {
      this.handleBridgeReconnected();
    });
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
      getRunningCorePIDs: callbacks.getRunningCorePIDs,
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
    ipcMain.on(IpcCommands.SYNC_GET_DEBUG, (event) => {
      event.returnValue = this.systemHandlers.getDebugSettings();
    });
    ipcMain.on(IpcCommands.SYNC_API_URL, (event) => {
      event.returnValue = this.systemHandlers.getApiUrls();
    });
    ipcMain.on(IpcCommands.PREMIUM_LOGIN, (_event, showPremium) => {
      callbacks.updatePremiumMenu(showPremium);
    });
    ipcMain.handle(IpcCommands.INVOKE_CLOSE_APP, callbacks.quit);
    ipcMain.handle(IpcCommands.INVOKE_OPEN_URL, async (_, url: string) => this.systemHandlers.openUrl(url));
    ipcMain.handle(IpcCommands.INVOKE_OPEN_DIRECTORY, async (_, title: string, defaultPath?: string) => this.systemHandlers.openDirectory(title, defaultPath));
    ipcMain.handle(IpcCommands.INVOKE_OPEN_PATH, (_, path: string) => this.systemHandlers.openPath(path));
    ipcMain.handle(IpcCommands.INVOKE_CONFIG, async (_, defaultConfig: boolean) => this.systemHandlers.getConfig(defaultConfig));
    ipcMain.handle(IpcCommands.INVOKE_VERSION, () => this.systemHandlers.getVersion());
    ipcMain.handle(IpcCommands.INVOKE_IS_MAC, () => this.systemHandlers.getIsMac());
    ipcMain.handle(IpcCommands.INVOKE_THEME, (_, selectedTheme: number) => this.systemHandlers.setSelectedTheme(selectedTheme));
    ipcMain.on(IpcCommands.LOG_TO_FILE, (_, level: LogLevel, message: string) => {
      this.systemHandlers.logToFile(level, message);
    });
    ipcMain.on(IpcCommands.TRAY_UPDATE, (_event, trayUpdate: TrayUpdate) => {
      this.systemHandlers.updateTray(trayUpdate);
    });

    // Backend handlers
    ipcMain.handle(IpcCommands.INVOKE_SUBPROCESS_START, async (event, options) => this.backendHandlers.restartBackend(options, event));

    // Update handlers
    ipcMain.handle(IpcCommands.INVOKE_UPDATE_CHECK, this.updateHandlers.checkForUpdates);
    ipcMain.handle(IpcCommands.INVOKE_DOWNLOAD_UPDATE, this.updateHandlers.downloadUpdate);
    ipcMain.handle(IpcCommands.INVOKE_INSTALL_UPDATE, this.updateHandlers.installUpdate);

    // Security handlers
    ipcMain.handle(IpcCommands.INVOKE_STORE_PASSWORD, async (_, credentials: Credentials) => this.securityHandlers.storePassword(credentials));
    ipcMain.handle(IpcCommands.INVOKE_GET_PASSWORD, async (_, username: string) => this.securityHandlers.getPassword(username));
    ipcMain.handle(IpcCommands.INVOKE_CLEAR_PASSWORD, async () => this.securityHandlers.clearPassword());

    // Wallet import handlers
    ipcMain.handle(IpcCommands.INVOKE_WALLET_IMPORT, this.walletImportHandlers.importFromWallet);

    // Wallet bridge IPC handlers
    ipcMain.handle(IpcCommands.OPEN_WALLET_CONNECT_BRIDGE, this.walletBridgeIpcHandlers.openWalletConnectBridge);
    ipcMain.handle(IpcCommands.WALLET_BRIDGE_HTTP_LISTENING, this.walletBridgeIpcHandlers.handleWalletBridgeHttpListening);
    ipcMain.handle(IpcCommands.WALLET_BRIDGE_WS_LISTENING, this.walletBridgeIpcHandlers.handleWalletBridgeWsListening);
    ipcMain.handle(IpcCommands.WALLET_BRIDGE_CLIENT_READY, this.walletBridgeIpcHandlers.handleWalletBridgeClientReady);
    ipcMain.on(IpcCommands.USER_LOGOUT, this.walletBridgeIpcHandlers.handleUserLogout);

    // Wallet Bridge handlers (from existing handler class)
    ipcMain.handle(IpcCommands.WALLET_BRIDGE_REQUEST, this.walletBridgeHandlers.handleWalletBridgeRequest);
    ipcMain.handle(IpcCommands.WALLET_BRIDGE_IS_CLIENT_CONNECTED, this.walletBridgeHandlers.handleWalletBridgeConnectionStatus);
    ipcMain.handle(IpcCommands.WALLET_BRIDGE_STOP_SERVERS, this.walletBridgeIpcHandlers.handleStopServers);

    // EIP-6963 Provider Detection handlers
    ipcMain.handle(IpcCommands.WALLET_BRIDGE_GET_PROVIDERS, this.walletBridgeIpcHandlers.getAvailableProviders);
    ipcMain.handle(IpcCommands.WALLET_BRIDGE_SELECT_PROVIDER, this.walletBridgeIpcHandlers.selectProvider);
    ipcMain.handle(IpcCommands.WALLET_BRIDGE_GET_SELECTED_PROVIDER, this.walletBridgeIpcHandlers.getSelectedProvider);
  }

  cleanup(): void {
    this.logger.info('Cleaning up IPC manager resources...');

    // Stop WebSocket server
    this.walletBridgeWebSocketServer.stop();

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
