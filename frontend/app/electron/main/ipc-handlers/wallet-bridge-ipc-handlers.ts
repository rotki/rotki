import type { LogService } from '@electron/main/log-service';
import type { WalletBridgeWebSocketServer } from '@electron/main/ws';
import { AppServer } from '@electron/main/app-server';
import { selectPort } from '@electron/main/port-utils';
import { shell } from 'electron';

interface WalletBridgeIpcHandlersCallbacks {
  sendIpcMessage: (channel: string, ...args: any[]) => void;
}

export class WalletBridgeIpcHandlers {
  private callbacks: WalletBridgeIpcHandlersCallbacks | null = null;
  private walletConnectBridgePort: number | undefined = undefined;
  private readonly appServer: AppServer;

  private get requireCallbacks(): WalletBridgeIpcHandlersCallbacks {
    const callbacks = this.callbacks;
    if (!callbacks) {
      throw new Error('WalletBridgeIpcHandlers callbacks not initialized');
    }
    return callbacks;
  }

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
          // Everything is running and connected, open the page
          this.logger.info(`Wallet Connect Bridge already running and connected at http://localhost:${this.walletConnectBridgePort}, opening page`);
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
}
