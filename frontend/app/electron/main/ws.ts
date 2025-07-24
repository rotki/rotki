import type { LogService } from '@electron/main/log-service';
import type { WalletBridgeNotification, WalletBridgeRequest } from '@electron/main/wallet-bridge-types';
import type { RpcRequest } from '@/types';
import { WalletBridgeNotConnectedError, WalletBridgeTimeoutError } from '@electron/main/wallet-bridge-errors';
import { ROTKI_RPC_METHODS, ROTKI_RPC_RESPONSES } from '@shared/proxy/constants';
import { WebSocketServer } from 'ws';
import { WalletBridgeConnectionManager } from './wallet-bridge-connection-manager';
import { WalletBridgeMessageHandler } from './wallet-bridge-message-handler';
import {
  IDLE_TIMEOUT_MS,
  type PendingRequest,
  REQUEST_TIMEOUT_MS,
  type WalletBridgeIpcCallbacks,
  WEBSOCKET_PATH,
} from './wallet-bridge-ws-types';

/**
 * WebSocket server for managing wallet bridge connections
 */
export class WalletBridgeWebSocketServer {
  private wsServer: WebSocketServer | undefined;
  private readonly pendingRequests = new Map<string, PendingRequest>();
  private idleTimer?: NodeJS.Timeout;
  private requestIdNonce = 0;
  private connectionManager: WalletBridgeConnectionManager;
  private messageHandler: WalletBridgeMessageHandler;

  constructor(private readonly logger: LogService) {
    this.connectionManager = new WalletBridgeConnectionManager(logger);
    this.messageHandler = new WalletBridgeMessageHandler(
      logger,
      this.pendingRequests,
      () => this.connectionManager.getActiveConnectionId(),
    );
  }

  /** Start the WebSocket server on the specified port */
  public start(port: number): void {
    if (this.wsServer) {
      return; // Already started
    }

    this.wsServer = new WebSocketServer({
      port,
      path: WEBSOCKET_PATH,
    });

    this.wsServer.on('connection', (ws) => {
      const shouldNotifyReconnection = this.connectionManager.shouldNotifyReconnection();

      // Register the new connection
      const currentConnectionId = this.connectionManager.registerConnection(ws);

      // Handle connection takeover if needed
      this.connectionManager.handleConnectionTakeover(
        currentConnectionId,
        connectionId => this.cancelPendingRequestsForConnection(connectionId),
      );

      // Notify about connection status
      this.connectionManager.notifyConnectionStatus(port, shouldNotifyReconnection);

      // Start idle timer when connection is established
      this.resetIdleTimer();

      ws.on('message', (data) => {
        const messageString = typeof data === 'string' ? data : data.toString();
        this.messageHandler.handleMessage(messageString, () => this.resetIdleTimer());
      });

      ws.on('close', () => {
        this.connectionManager.handleConnectionClose(
          ws,
          connectionId => this.cancelPendingRequestsForConnection(connectionId),
        );
        this.clearIdleTimer();
      });

      ws.on('error', (error) => {
        this.logger.error('Wallet bridge WebSocket error:', error);
      });
    });

    this.wsServer.on('error', (error) => {
      this.logger.error('WebSocket server error:', error);
    });

    this.logger.info(`Wallet bridge WebSocket server started at ws://localhost:${port}${WEBSOCKET_PATH}`);
  }

  private resetIdleTimer(): void {
    if (this.idleTimer) {
      clearTimeout(this.idleTimer);
    }

    this.idleTimer = setTimeout(() => {
      this.logger.info('WebSocket connection idle timeout reached, closing connection');
      this.disconnect();
    }, IDLE_TIMEOUT_MS);
  }

  private clearIdleTimer(): void {
    if (this.idleTimer) {
      clearTimeout(this.idleTimer);
      this.idleTimer = undefined;
    }
  }

  private getNextRequestId(): string {
    return `req_${++this.requestIdNonce}`;
  }

  /** Send an RPC request to the wallet bridge */
  public async sendToWalletBridge(message: RpcRequest): Promise<any> {
    return new Promise((resolve, reject) => {
      const activeConnection = this.connectionManager.getActiveConnection();
      if (!activeConnection || activeConnection.readyState !== activeConnection.OPEN) {
        reject(new WalletBridgeNotConnectedError());
        return;
      }

      // Generate id and add jsonrpc to create a proper WebSocket message
      const id = this.getNextRequestId();
      const requestMessage: WalletBridgeRequest = {
        ...message,
        id,
        jsonrpc: '2.0',
      };

      // Store the promise handlers with current connection ID
      this.pendingRequests.set(id, {
        resolve,
        reject,
        connectionId: this.connectionManager.getActiveConnectionId(),
      });

      // Reset idle timer on outgoing messages
      this.resetIdleTimer();

      // Send message to wallet bridge
      activeConnection.send(JSON.stringify(requestMessage));

      // Set timeout for the request
      setTimeout(() => {
        if (this.pendingRequests.has(id)) {
          this.pendingRequests.delete(id);
          reject(new WalletBridgeTimeoutError());
        }
      }, REQUEST_TIMEOUT_MS);
    });
  }

  /** Check if the WebSocket connection is active */
  public isConnected(): boolean {
    const activeConnection = this.connectionManager.getActiveConnection();
    return activeConnection ? activeConnection.readyState === activeConnection.OPEN : false;
  }

  /** Verify the client can handle requests */
  public async isClientReady(): Promise<boolean> {
    if (!this.isConnected()) {
      return false;
    }

    try {
      // Send a ping to verify the client can handle requests
      const pingResponse = await this.sendToWalletBridge({
        method: ROTKI_RPC_METHODS.PING,
        params: [],
      });

      return pingResponse === ROTKI_RPC_RESPONSES.PONG;
    }
    catch (error) {
      // If the request fails due to timeout or connection issues, client is not ready
      this.logger.debug('Client readiness check failed:', error);
      return false;
    }
  }

  /** Send a notification to the wallet bridge */
  public sendNotification(message: WalletBridgeNotification): void {
    // Get the active connection
    const connection = this.connectionManager.getActiveConnection();

    if (!connection) {
      this.logger.warn('Cannot send notification: No active bridge connection');
      return;
    }

    // Check connection state
    if (connection.readyState !== connection.OPEN) {
      this.logger.warn(`Cannot send notification: Connection state is ${connection.readyState} (not OPEN)`);
      return;
    }

    try {
      connection.send(JSON.stringify(message));
      this.logger.info(`Notification sent to wallet bridge connection ${this.connectionManager.getActiveConnectionId()}: ${message.type}`);
    }
    catch (error) {
      this.logger.error('Failed to send notification to wallet bridge:', error);
      throw error; // Re-throw so caller can handle it
    }
  }

  /** Check if the server is listening */
  public isListening(): boolean {
    return !!this.wsServer;
  }

  /** Disconnect all connections and stop the server */
  public disconnect(): void {
    // Clear idle timer
    this.clearIdleTimer();

    // Close active connection if it exists
    const activeConnection = this.connectionManager.getActiveConnection();
    if (activeConnection) {
      activeConnection.close();
    }

    // Clear all connection mappings
    this.connectionManager.clearAll();

    if (this.wsServer) {
      this.wsServer.close();
      this.wsServer = undefined;
    }

    // Reject all pending requests
    this.pendingRequests.forEach(({ reject }) => {
      reject(new Error('Wallet bridge disconnected'));
    });
    this.pendingRequests.clear();
  }

  /** Stop the server (alias for disconnect) */
  public stop(): void {
    this.disconnect();
  }

  public setOnBridgeDisconnected(callback: () => void): void {
    this.connectionManager = new WalletBridgeConnectionManager(
      this.logger,
      callback,
      undefined,
    );
  }

  public setOnBridgeReconnected(callback: () => void): void {
    this.connectionManager = new WalletBridgeConnectionManager(
      this.logger,
      undefined,
      callback,
    );
  }

  public setIpcCallbacks(callbacks: WalletBridgeIpcCallbacks): void {
    this.connectionManager = new WalletBridgeConnectionManager(
      this.logger,
      undefined,
      undefined,
      callbacks,
    );
    this.messageHandler = new WalletBridgeMessageHandler(
      this.logger,
      this.pendingRequests,
      () => this.connectionManager.getActiveConnectionId(),
      callbacks,
    );
  }

  private cancelPendingRequestsForConnection(connectionId: number): void {
    const requestsToCancel: string[] = [];

    for (const [requestId, requestInfo] of this.pendingRequests) {
      if (requestInfo.connectionId === connectionId) {
        requestsToCancel.push(requestId);
        requestInfo.reject(new Error(`Connection ${connectionId} was closed`));
      }
    }

    for (const requestId of requestsToCancel) {
      this.pendingRequests.delete(requestId);
    }

    if (requestsToCancel.length > 0) {
      this.logger.info(`Cancelled ${requestsToCancel.length} pending requests for connection ${connectionId}`);
    }
  }
}
