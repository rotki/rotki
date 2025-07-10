import type { LogService } from '@electron/main/log-service';
import type { WalletBridgeWebSocketServer } from '@electron/main/ws';
import type { WalletBridgeRequest, WalletBridgeResponse } from '@shared/ipc';
import { WalletBridgeNotConnectedError } from '@electron/main/wallet-bridge-errors';

export class WalletBridgeHandlers {
  constructor(
    private readonly logger: LogService,
    private readonly wsServer: WalletBridgeWebSocketServer,
  ) {}

  readonly handleWalletBridgeRequest = async (
    _event: Electron.IpcMainInvokeEvent,
    request: WalletBridgeRequest,
  ): Promise<WalletBridgeResponse> => {
    try {
      this.logger.debug(`Wallet bridge request: ${request.method}`);

      if (!this.wsServer.isConnected()) {
        return {
          error: {
            code: -32603,
            message: 'Wallet bridge not connected',
          },
        };
      }

      const result = await this.wsServer.sendToWalletBridge(request);

      this.logger.debug(`Wallet bridge response: ${JSON.stringify(result)}`);

      return {
        result,
      };
    }
    catch (error: any) {
      // For connection errors, log as warning without stack trace
      if (error instanceof WalletBridgeNotConnectedError) {
        this.logger.warn(`Wallet bridge request failed: ${error.message}`);
      }
      else {
        this.logger.error('Wallet bridge request failed:', error);
      }

      // Use the error's code if it's a WalletBridgeError
      const errorCode = error.code ?? -32603;

      return {
        error: {
          code: errorCode,
          message: error.message ?? 'Internal error',
        },
      };
    }
  };

  readonly handleWalletBridgeConnect = async (
    _event: Electron.IpcMainInvokeEvent,
  ): Promise<boolean> => {
    try {
      return this.wsServer.isConnected();
    }
    catch (error: any) {
      this.logger.error('Failed to connect wallet bridge:', error);
      return false;
    }
  };

  readonly handleWalletBridgeDisconnect = async (
    _event: Electron.IpcMainInvokeEvent,
  ): Promise<void> => {
    try {
      this.logger.info('Disabling wallet bridge connection');
      this.wsServer.disconnect();
    }
    catch (error: any) {
      this.logger.error('Failed to disconnect wallet bridge:', error);
    }
  };
}
