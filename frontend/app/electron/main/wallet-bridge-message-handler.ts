import type { LogService } from '@electron/main/log-service';
import { WalletBridgeMessageSchema, WalletBridgeResponseSchema } from '@shared/wallet-bridge-types';
import { IPC_BRIDGE_EVENT_CHANNEL, type PendingRequest, type WalletBridgeIpcCallbacks } from './wallet-bridge-ws-types';

/**
 * Handles WebSocket message parsing and routing for the wallet bridge
 */
export class WalletBridgeMessageHandler {
  constructor(
    private readonly logger: LogService,
    private readonly pendingRequests: Map<string, PendingRequest>,
    private readonly getActiveConnectionId: () => number,
    private readonly ipcCallbacks?: WalletBridgeIpcCallbacks,
  ) {}

  /**
   * Handle incoming WebSocket messages
   */
  handleMessage(message: string, resetIdleTimer: () => void): void {
    try {
      const rawData = JSON.parse(message);
      const parseResult = WalletBridgeMessageSchema.safeParse(rawData);

      if (!parseResult.success) {
        this.logger.error('Invalid WebSocket message schema:', parseResult.error);
        return;
      }

      const data = parseResult.data;
      resetIdleTimer();

      // Handle responses from wallet-bridge page
      if ('id' in data && data.id && this.pendingRequests.has(String(data.id))) {
        this.handleResponse(data);
      }
      // Handle wallet event notifications
      else if ('type' in data && data.type === 'wallet_event' && 'eventName' in data) {
        this.handleWalletEvent(data);
      }
    }
    catch (error) {
      this.logger.error('Invalid WebSocket message:', error);
    }
  }

  /**
   * Handle RPC responses from the wallet bridge
   */
  private handleResponse(data: any): void {
    const responseResult = WalletBridgeResponseSchema.safeParse(data);
    if (!responseResult.success) {
      return;
    }

    const response = responseResult.data;
    const requestId = String(data.id);
    const requestInfo = this.pendingRequests.get(requestId);
    if (!requestInfo) {
      this.logger.warn(`No pending request found for ID: ${data.id}`);
      return;
    }

    // Verify this response is from the current active connection
    if (requestInfo.connectionId === this.getActiveConnectionId()) {
      const { resolve, reject } = requestInfo;
      this.pendingRequests.delete(requestId);

      if (response.error) {
        const error = new Error(response.error.message) as Error & { code?: number };
        error.code = response.error.code;
        reject(error);
      }
      else {
        resolve(response.result);
      }
    }
    else {
      this.logger.warn(`Ignoring response from old connection. Request connection ID: ${requestInfo.connectionId}, current: ${this.getActiveConnectionId()}`);
      this.pendingRequests.delete(requestId);
    }
  }

  /**
   * Handle wallet event notifications
   */
  private handleWalletEvent(data: any): void {
    this.logger.debug(`Received wallet event: ${data.eventName}`, data.eventData);

    if (this.ipcCallbacks) {
      this.ipcCallbacks.sendIpcMessage(IPC_BRIDGE_EVENT_CHANNEL, {
        eventName: data.eventName,
        eventData: data.eventData,
      });
    }
  }
}
