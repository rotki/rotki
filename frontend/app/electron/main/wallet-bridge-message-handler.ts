import type { LogService } from '@electron/main/log-service';
import {
  parseWalletBridgeMessage,
  type WalletBridgeMessage,
  type WalletBridgeNotification,
  WalletBridgeResponseSchema,
} from '@shared/wallet-bridge-types';
import { IPC_BRIDGE_EVENT_CHANNEL, type PendingRequest, type WalletBridgeIpcCallbacks } from './wallet-bridge-ws-types';

/**
 * Handles WebSocket message parsing and routing for the wallet bridge
 */
export class WalletBridgeMessageHandler {
  private ipcCallbacks?: WalletBridgeIpcCallbacks;

  constructor(
    private readonly logger: LogService,
    private readonly pendingRequests: Map<string, PendingRequest>,
    private readonly getActiveConnectionId: () => number,
  ) {}

  setIpcCallbacks(callbacks: WalletBridgeIpcCallbacks): void {
    this.ipcCallbacks = callbacks;
  }

  /**
   * Handle incoming WebSocket messages
   */
  handleMessage(message: string, resetIdleTimer: () => void): void {
    const parsed = parseWalletBridgeMessage(message);
    if (!parsed.ok) {
      this.logger.error(`Invalid WebSocket message (${parsed.error.kind}):`, parsed.error.cause);
      return;
    }

    resetIdleTimer();
    this.routeMessage(parsed.value);
  }

  private routeMessage(data: WalletBridgeMessage): void {
    if ('id' in data && data.id && this.pendingRequests.has(String(data.id)))
      this.handleResponse(data);
    else if ('type' in data && data.type === 'wallet_event' && 'eventName' in data)
      this.handleWalletEvent(data);
  }

  /**
   * Handle RPC responses from the wallet bridge
   *
   * @remarks
   * Deleting the pending entry disarms the request timeout, so every branch after it must settle
   * the promise or the caller waits forever.
   */
  private handleResponse(data: WalletBridgeMessage): void {
    const responseResult = WalletBridgeResponseSchema.safeParse(data);
    if (!responseResult.success) {
      this.logger.warn('Ignoring a message that reuses a pending request id but is not a response');
      return;
    }

    const response = responseResult.data;
    const requestId = String(response.id);
    const requestInfo = this.pendingRequests.get(requestId);
    if (!requestInfo) {
      this.logger.warn(`No pending request found for ID: ${response.id}`);
      return;
    }

    const { resolve, reject, connectionId } = requestInfo;
    this.pendingRequests.delete(requestId);

    if (connectionId !== this.getActiveConnectionId()) {
      this.logger.warn(`Ignoring response from old connection. Request connection ID: ${connectionId}, current: ${this.getActiveConnectionId()}`);
      reject(new Error(`Connection ${connectionId} was replaced before it responded`));
    }
    else if (response.error) {
      reject(Object.assign(new Error(response.error.message), { code: response.error.code }));
    }
    else {
      resolve(response.result);
    }
  }

  /**
   * Handle wallet event notifications
   */
  private handleWalletEvent(data: WalletBridgeNotification): void {
    this.logger.debug(`Received wallet event: ${data.eventName}`, data.eventData);

    if (this.ipcCallbacks) {
      this.ipcCallbacks.sendIpcMessage(IPC_BRIDGE_EVENT_CHANNEL, {
        eventName: data.eventName,
        eventData: data.eventData,
      });
    }
  }
}
