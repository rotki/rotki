import type { LogService } from '@electron/main/log-service';
import type { WebSocket } from 'ws';
import { IPC_CONNECTION_STATUS_CHANNEL, type WalletBridgeIpcCallbacks } from './wallet-bridge-ws-types';

/**
 * Manages WebSocket connections for the wallet bridge
 */
export class WalletBridgeConnectionManager {
  private activeConnectionId = 0;
  private connectionIdCounter = 0;
  private readonly connectionIds = new Map<WebSocket, number>();
  private readonly connectionsById = new Map<number, WebSocket>();
  private disconnectedState = false;

  constructor(
    private readonly logger: LogService,
    private readonly onBridgeDisconnected?: () => void,
    private readonly onBridgeReconnected?: () => void,
    private readonly ipcCallbacks?: WalletBridgeIpcCallbacks,
  ) {}

  /**
   * Register a new WebSocket connection
   */
  registerConnection(ws: WebSocket): number {
    const connectionId = ++this.connectionIdCounter;
    this.connectionIds.set(ws, connectionId);
    this.connectionsById.set(connectionId, ws);
    this.logger.info(`New wallet bridge connection (ID: ${connectionId}) detected`);
    return connectionId;
  }

  /**
   * Handle connection takeover when a new connection replaces an existing one
   */
  handleConnectionTakeover(
    newConnectionId: number,
    cancelPendingRequests: (connectionId: number) => void,
  ): void {
    const oldConnection = this.getActiveConnection();
    if (oldConnection && oldConnection.readyState === oldConnection.OPEN) {
      const oldConnectionId = this.activeConnectionId;
      this.logger.info(`Taking over from existing connection (ID: ${oldConnectionId})`);

      try {
        const takeoverNotification = { type: 'reconnected' as const };
        oldConnection.send(JSON.stringify(takeoverNotification));
        this.logger.info(`Sent reconnected notification to connection ID: ${oldConnectionId}`);
      }
      catch (error) {
        this.logger.error('Failed to send reconnected notification:', error);
      }

      oldConnection.close();
      this.connectionIds.delete(oldConnection);
      this.connectionsById.delete(oldConnectionId);
      cancelPendingRequests(oldConnectionId);
    }

    this.activeConnectionId = newConnectionId;
    this.disconnectedState = false;
  }

  /**
   * Handle connection close events
   */
  handleConnectionClose(
    ws: WebSocket,
    cancelPendingRequests: (connectionId: number) => void,
  ): void {
    const wsConnectionId = this.connectionIds.get(ws);

    this.connectionIds.delete(ws);
    if (wsConnectionId) {
      this.connectionsById.delete(wsConnectionId);
    }

    if (wsConnectionId === this.activeConnectionId) {
      this.activeConnectionId = 0;
      this.disconnectedState = true;
      this.logger.info(`Active wallet bridge connection (ID: ${wsConnectionId}) disconnected`);

      cancelPendingRequests(wsConnectionId);

      if (this.onBridgeDisconnected) {
        this.onBridgeDisconnected();
      }
      if (this.ipcCallbacks) {
        this.ipcCallbacks.sendIpcMessage(IPC_CONNECTION_STATUS_CHANNEL, 'disconnected');
      }
    }
    else {
      this.logger.info(`Old wallet bridge connection (ID: ${wsConnectionId}) closed (takeover completed)`);
      if (wsConnectionId) {
        cancelPendingRequests(wsConnectionId);
      }
    }
  }

  /**
   * Send connection status notifications
   */
  notifyConnectionStatus(port: number, isReconnection: boolean): void {
    if (isReconnection) {
      this.logger.info(`Wallet bridge WebSocket reconnected on port ${port}`);
      if (this.onBridgeReconnected) {
        this.onBridgeReconnected();
      }
      if (this.ipcCallbacks) {
        this.ipcCallbacks.sendIpcMessage(IPC_CONNECTION_STATUS_CHANNEL, 'reconnected');
      }
    }
    else {
      this.logger.info(`Wallet bridge WebSocket connected on port ${port}`);
      if (this.ipcCallbacks) {
        this.ipcCallbacks.sendIpcMessage(IPC_CONNECTION_STATUS_CHANNEL, 'connected');
      }
    }
  }

  /**
   * Get the currently active WebSocket connection
   */
  getActiveConnection(): WebSocket | undefined {
    return this.connectionsById.get(this.activeConnectionId);
  }

  /**
   * Get the active connection ID
   */
  getActiveConnectionId(): number {
    return this.activeConnectionId;
  }

  /**
   * Check if there was a previous connection or disconnected state
   */
  shouldNotifyReconnection(): boolean {
    return this.activeConnectionId !== 0 || this.disconnectedState;
  }

  /**
   * Clear all connection mappings
   */
  clearAll(): void {
    this.connectionIds.clear();
    this.connectionsById.clear();
    this.activeConnectionId = 0;
    this.disconnectedState = true;
  }
}
