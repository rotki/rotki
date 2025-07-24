import type { LogService } from '@electron/main/log-service';
import type { WalletBridgeWebSocketServer } from '@electron/main/ws';
import type { EIP6963ProviderDetail } from '@/types';
import { AppServer } from '@electron/main/app-server';
import { selectPort } from '@electron/main/port-utils';
import { ROTKI_RPC_METHODS } from '@shared/proxy/constants';
import { shell } from 'electron';

interface WalletBridgeIpcHandlersCallbacks {
  sendIpcMessage: (channel: string, ...args: any[]) => void;
}

export class WalletBridgeIpcHandlers {
  private callbacks: WalletBridgeIpcHandlersCallbacks | null = null;
  private walletConnectBridgePort: number | undefined = undefined;
  private readonly appServer: AppServer;

  constructor(
    private readonly logger: LogService,
    private readonly walletBridgeWebSocketServer: WalletBridgeWebSocketServer,
  ) {
    this.appServer = new AppServer(logger);
  }

  initialize(callbacks: WalletBridgeIpcHandlersCallbacks): void {
    this.callbacks = callbacks;
    // Set the IPC callbacks on the WebSocket server
    this.walletBridgeWebSocketServer.setIpcCallbacks({
      sendIpcMessage: callbacks.sendIpcMessage,
    });
  }

  openWalletConnectBridge = async (): Promise<void> => {
    try {
      // Check if servers are already running
      const httpRunning = this.appServer.isListening();
      const wsRunning = this.walletBridgeWebSocketServer.isListening();
      const wsConnected = this.walletBridgeWebSocketServer.isConnected();

      if (this.walletConnectBridgePort && httpRunning && wsRunning) {
        if (wsConnected) {
          // Everything is running and connected, reset selected provider and open the page
          this.logger.info(`Wallet Connect Bridge already running and connected at http://localhost:${this.walletConnectBridgePort}, resetting provider selection and opening page`);
          await this.resetSelectedProvider();
          await shell.openExternal(`http://localhost:${this.walletConnectBridgePort}/#/wallet-bridge`);
        }
        else {
          // Servers are running but client is disconnected - reopen URL to reconnect
          this.logger.info(`Wallet Connect Bridge servers running but client disconnected, reopening URL to reconnect`);
          await shell.openExternal(`http://localhost:${this.walletConnectBridgePort}/#/wallet-bridge`);
        }
        return;
      }

      // Servers not running or not configured, start them
      const portNumber = await selectPort(40010);
      this.walletConnectBridgePort = portNumber; // Store the port

      this.appServer.start(portNumber, '/#/wallet-bridge');

      // Start WebSocket server alongside HTTP server
      this.walletBridgeWebSocketServer.start(portNumber + 1);

      // Small delay to ensure servers are ready
      await new Promise(resolve => setTimeout(resolve, 100));

      // Open the Wallet Connect Bridge in Electron (same URL in dev/prod)
      await shell.openExternal(`http://localhost:${portNumber}/#/wallet-bridge`);
    }
    catch (error: any) {
      this.logger.error(`Error opening Wallet Connect Bridge: ${error}`);
    }
  };

  handleWalletBridgeHttpListening = async (): Promise<boolean> => this.appServer.isListening();

  handleWalletBridgeWsListening = async (): Promise<boolean> => this.walletBridgeWebSocketServer.isListening();

  handleWalletBridgeClientReady = async (): Promise<boolean> => this.walletBridgeWebSocketServer.isClientReady();

  handleUserLogout = (): void => {
    this.logger.info('User logout event received, cleaning up wallet bridge connections');

    // Try to send close signal immediately and synchronously if possible
    this.sendCloseSignalAndCleanup();
  };

  private sendCloseSignalAndCleanup(): void {
    const wasConnected = this.walletBridgeWebSocketServer.isConnected();

    if (wasConnected) {
      this.logger.info('Sending close signal to bridge clients');

      // Try to send the notification immediately
      try {
        this.walletBridgeWebSocketServer.sendNotification({ type: 'close_tab' });

        // Wait a moment for the message to be sent before disconnecting
        setTimeout(() => {
          this.performCleanup();
        }, 150);
      }
      catch (error) {
        this.logger.warn('Failed to send close notification:', error);
        // Clean up immediately if we can't send the message
        this.performCleanup();
      }
    }
    else {
      // No connection, clean up immediately
      this.logger.info('No active bridge connection, cleaning up immediately');
      this.performCleanup();
    }
  }

  private performCleanup(): void {
    this.logger.info('Performing wallet bridge cleanup');

    // Disconnect wallet bridge WebSocket
    this.walletBridgeWebSocketServer.disconnect();

    // Stop app server
    this.appServer.stop();

    // Clear the stored port so it can be restarted fresh next time
    this.walletConnectBridgePort = undefined;
  }

  // EIP-6963 Provider Detection handlers
  getAvailableProviders = async (): Promise<any[]> => {
    try {
      this.logger.debug('Getting available EIP-6963 providers from bridge');

      if (!this.walletBridgeWebSocketServer.isConnected()) {
        this.logger.warn('Wallet bridge not connected for provider detection');
        return [];
      }

      const result = await this.walletBridgeWebSocketServer.sendToWalletBridge({
        method: ROTKI_RPC_METHODS.GET_AVAILABLE_PROVIDERS,
        params: [],
      });

      return result || [];
    }
    catch (error: any) {
      this.logger.error('Failed to get available providers:', error);
      return [];
    }
  };

  selectProvider = async (_event: Electron.IpcMainInvokeEvent, uuid: string): Promise<boolean> => {
    try {
      this.logger.debug(`Selecting EIP-6963 provider: ${uuid}`);

      if (!this.walletBridgeWebSocketServer.isConnected()) {
        this.logger.warn('Wallet bridge not connected for provider selection');
        return false;
      }

      const result = await this.walletBridgeWebSocketServer.sendToWalletBridge({
        method: ROTKI_RPC_METHODS.SELECT_PROVIDER,
        params: [uuid],
      });

      return result === true;
    }
    catch (error: any) {
      this.logger.error('Failed to select provider:', error);
      return false;
    }
  };

  getSelectedProvider = async (): Promise<EIP6963ProviderDetail | null> => {
    try {
      this.logger.debug('Getting selected provider from bridge');

      if (!this.walletBridgeWebSocketServer.isConnected()) {
        this.logger.warn('Wallet bridge not connected for getting selected provider');
        return null;
      }

      const result = await this.walletBridgeWebSocketServer.sendToWalletBridge({
        method: ROTKI_RPC_METHODS.GET_SELECTED_PROVIDER,
        params: [],
      });

      return result || null;
    }
    catch (error: any) {
      this.logger.error('Failed to get selected provider:', error);
      return null;
    }
  };

  private resetSelectedProvider = async (): Promise<void> => {
    try {
      this.logger.debug('Resetting selected provider in bridge');

      if (!this.walletBridgeWebSocketServer.isConnected()) {
        this.logger.warn('Wallet bridge not connected for resetting selected provider');
        return;
      }

      // Clear the selected provider by selecting an empty string or null
      await this.walletBridgeWebSocketServer.sendToWalletBridge({
        method: ROTKI_RPC_METHODS.SELECT_PROVIDER,
        params: [''],
      });

      this.logger.info('Successfully reset selected provider in bridge');
    }
    catch (error: any) {
      this.logger.error('Failed to reset selected provider:', error);
      // Don't throw error as this is not critical for opening the bridge
    }
  };
}
