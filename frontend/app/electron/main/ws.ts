import type { LogService } from '@electron/main/log-service';
import type { RpcRequest } from '@/types';
import { WalletBridgeNotConnectedError, WalletBridgeTimeoutError } from '@electron/main/wallet-bridge-errors';
import { WalletBridgeMessageSchema, type WalletBridgeNotification, type WalletBridgeRequest, WalletBridgeResponseSchema } from '@electron/main/wallet-bridge-types';
import { type WebSocket, WebSocketServer } from 'ws';

interface WalletBridgeIpcCallbacks {
  sendIpcMessage: (channel: string, ...args: any[]) => void;
}

export class WalletBridgeWebSocketServer {
  private wsServer: WebSocketServer | undefined;
  private activeBridgeConnection: WebSocket | undefined;
  private readonly pendingRequests = new Map<string, { resolve: (value: any) => void; reject: (error: any) => void }>();
  private onBridgeDisconnected?: () => void;
  private onBridgeReconnected?: () => void;
  private idleTimer?: NodeJS.Timeout;
  private readonly idleTimeout = 15 * 60 * 1000; // 15 minutes in milliseconds
  private disconnectedState = false;
  private requestIdNonce = 0;
  private ipcCallbacks?: WalletBridgeIpcCallbacks;

  constructor(private readonly logger: LogService) {}

  public start(port: number): void {
    if (this.wsServer) {
      return; // Already started
    }

    this.wsServer = new WebSocketServer({
      port,
      path: '/wallet-bridge',
    });

    this.wsServer.on('connection', (ws) => {
      const hadPreviousConnection = this.activeBridgeConnection !== undefined;
      const wasDisconnected = this.disconnectedState === true;

      // If there's already an active connection, notify it before taking over
      if (this.activeBridgeConnection && this.activeBridgeConnection.readyState === this.activeBridgeConnection.OPEN) {
        this.logger.info('New wallet bridge connection detected, taking over existing connection');

        // Send notification to existing connection before closing it
        try {
          const takeoverNotification = { type: 'reconnected' as const };
          this.activeBridgeConnection.send(JSON.stringify(takeoverNotification));
          this.logger.info('Sent reconnected notification to existing connection');
        }
        catch (error) {
          this.logger.error('Failed to send reconnected notification:', error);
        }

        // Close the existing connection
        this.activeBridgeConnection.close();
      }

      // Set new connection as active
      this.activeBridgeConnection = ws;
      this.disconnectedState = false;

      if (hadPreviousConnection || wasDisconnected) {
        this.logger.info(`Wallet bridge WebSocket reconnected on port ${port}`);
        // Notify that the bridge has been reconnected
        if (this.onBridgeReconnected) {
          this.onBridgeReconnected();
        }
        // Fire IPC event for reconnection
        if (this.ipcCallbacks) {
          this.ipcCallbacks.sendIpcMessage('WALLET_BRIDGE_CONNECTION_STATUS', 'reconnected');
        }
      }
      else {
        this.logger.info(`Wallet bridge WebSocket connected on port ${port}`);
        // Fire IPC event for initial connection
        if (this.ipcCallbacks) {
          this.ipcCallbacks.sendIpcMessage('WALLET_BRIDGE_CONNECTION_STATUS', 'connected');
        }
      }

      // Start idle timer when connection is established
      this.resetIdleTimer();

      ws.on('message', (data) => {
        this.handleWebSocketMessage(data.toString());
      });

      ws.on('close', () => {
        // Only mark as disconnected if this was the active connection
        // and no new connection has taken over
        if (this.activeBridgeConnection === ws) {
          this.activeBridgeConnection = undefined;
          this.disconnectedState = true;
          this.logger.info('Wallet bridge WebSocket disconnected');

          // Clear idle timer on disconnect
          this.clearIdleTimer();

          // Notify that the bridge has been disconnected
          if (this.onBridgeDisconnected) {
            this.onBridgeDisconnected();
          }
          // Fire IPC event for disconnection
          if (this.ipcCallbacks) {
            this.ipcCallbacks.sendIpcMessage('WALLET_BRIDGE_CONNECTION_STATUS', 'disconnected');
          }
        }
        else {
          this.logger.info('Old wallet bridge connection closed (takeover completed)');
        }
      });

      ws.on('error', (error) => {
        this.logger.error('Wallet bridge WebSocket error:', error);
      });
    });

    this.wsServer.on('error', (error) => {
      this.logger.error('WebSocket server error:', error);
    });

    this.logger.info(`Wallet bridge WebSocket server started at ws://localhost:${port}/wallet-bridge`);
  }

  private handleWebSocketMessage(message: string): void {
    try {
      const rawData = JSON.parse(message);
      const parseResult = WalletBridgeMessageSchema.safeParse(rawData);

      if (!parseResult.success) {
        this.logger.error('Invalid WebSocket message schema:', parseResult.error);
        return;
      }

      const data = parseResult.data;

      // Reset idle timer on any message
      this.resetIdleTimer();

      // Handle responses from wallet-bridge page
      if ('id' in data && data.id && this.pendingRequests.has(data.id)) {
        const responseResult = WalletBridgeResponseSchema.safeParse(data);

        if (responseResult.success) {
          const response = responseResult.data;
          const { resolve, reject } = this.pendingRequests.get(data.id)!;
          this.pendingRequests.delete(data.id);

          // Check if the response contains an error
          if (response.error) {
            // Create an error object with the code property
            const error = new Error(response.error.message);
            (error as any).code = response.error.code;
            reject(error);
          }
          else {
            resolve(response.result);
          }
        }
      }
      // Handle wallet event notifications
      else if ('type' in data && data.type === 'wallet_event' && 'eventName' in data) {
        this.logger.debug(`Received wallet event: ${data.eventName}`, data.eventData);

        // Forward wallet event via IPC using single channel
        if (this.ipcCallbacks) {
          this.ipcCallbacks.sendIpcMessage('WALLET_BRIDGE_EVENT', {
            eventName: data.eventName,
            eventData: data.eventData,
          });
        }
      }
    }
    catch (error) {
      this.logger.error('Invalid WebSocket message:', error);
    }
  }

  private resetIdleTimer(): void {
    if (this.idleTimer) {
      clearTimeout(this.idleTimer);
    }

    this.idleTimer = setTimeout(() => {
      this.logger.info('WebSocket connection idle timeout reached, closing connection');
      this.disconnect();
    }, this.idleTimeout);
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

  public async sendToWalletBridge(message: RpcRequest): Promise<any> {
    return new Promise((resolve, reject) => {
      if (!this.activeBridgeConnection || this.activeBridgeConnection.readyState !== this.activeBridgeConnection.OPEN) {
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

      // Store the promise handlers
      this.pendingRequests.set(id, { resolve, reject });

      // Reset idle timer on outgoing messages
      this.resetIdleTimer();

      // Send message to wallet bridge
      this.activeBridgeConnection.send(JSON.stringify(requestMessage));

      // Set timeout for the request
      setTimeout(() => {
        if (this.pendingRequests.has(id)) {
          this.pendingRequests.delete(id);
          reject(new WalletBridgeTimeoutError());
        }
      }, 30000);
    });
  }

  public isConnected(): boolean {
    return this.activeBridgeConnection?.readyState === this.activeBridgeConnection?.OPEN;
  }

  public sendNotification(message: WalletBridgeNotification): void {
    // Capture the connection reference immediately to avoid race conditions
    const connection = this.activeBridgeConnection;

    if (!connection) {
      this.logger.warn('Cannot send notification: No active bridge connection');
      return;
    }

    // Check connection state at the moment we captured it
    if (connection.readyState !== connection.OPEN) {
      this.logger.warn(`Cannot send notification: Connection state is ${connection.readyState} (not OPEN)`);
      return;
    }

    try {
      connection.send(JSON.stringify(message));
      this.logger.info(`Notification sent to wallet bridge: ${message.type}`);
    }
    catch (error) {
      this.logger.error('Failed to send notification to wallet bridge:', error);
      throw error; // Re-throw so caller can handle it
    }
  }

  public isListening(): boolean {
    return !!this.wsServer;
  }

  public disconnect(): void {
    // Clear idle timer
    this.clearIdleTimer();

    if (this.activeBridgeConnection) {
      this.activeBridgeConnection.close();
      this.activeBridgeConnection = undefined;
    }

    this.disconnectedState = true;

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

  public stop(): void {
    this.disconnect();
  }

  public setOnBridgeDisconnected(callback: () => void): void {
    this.onBridgeDisconnected = callback;
  }

  public setOnBridgeReconnected(callback: () => void): void {
    this.onBridgeReconnected = callback;
  }

  public setIpcCallbacks(callbacks: WalletBridgeIpcCallbacks): void {
    this.ipcCallbacks = callbacks;
  }
}
