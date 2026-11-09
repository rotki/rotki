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
  private ipcCallbacks?: WalletBridgeIpcCallbacks;

  constructor(private readonly logger: LogService) {}

  /** Set in place, so connections registered before the callbacks arrive are kept. */
  setIpcCallbacks(callbacks: WalletBridgeIpcCallbacks): void {
    this.ipcCallbacks = callbacks;
  }

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
   *
   * @returns whether the closed socket was the active connection; a superseded socket closing
   * after a takeover returns false and must not touch state that belongs to its successor.
   */
  handleConnectionClose(
    ws: WebSocket,
    cancelPendingRequests: (connectionId: number) => void,
  ): boolean {
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

      if (this.ipcCallbacks) {
        this.ipcCallbacks.sendIpcMessage(IPC_CONNECTION_STATUS_CHANNEL, 'disconnected');
      }
      return true;
    }

    if (wsConnectionId) {
      this.logger.info(`Old wallet bridge connection (ID: ${wsConnectionId}) closed`);
      cancelPendingRequests(wsConnectionId);
    }
    else {
      this.logger.info('Superseded wallet bridge connection closed (takeover completed)');
    }
    return false;
  }

  /**
   * Send connection status notifications
   */
  notifyConnectionStatus(port: number, isReconnection: boolean): void {
    if (isReconnection) {
      this.logger.info(`Wallet bridge WebSocket reconnected on port ${port}`);
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
