import type { EIP1193Provider, EIP1193ProviderEvents } from '@/types';
import { get, set } from '@vueuse/core';
import { computed, type ComputedRef, ref, type Ref } from 'vue';
import { logger } from '@/utils/logging';
import {
  type ConnectionStatus,
  isWalletBridgeNotification,
  isWalletBridgeRequest,
  validateWalletBridgeMessage,
  type WalletBridgeEventName,
  type WalletBridgeNotification,
  type WalletBridgeRequest,
  type WalletBridgeResponse,
} from './types';

type MessageHandler = (message: WalletBridgeRequest) => void;

type NotificationHandler = (notification: WalletBridgeNotification) => void;

type ConnectionHandler = (status: ConnectionStatus) => void;

export interface WalletBridgeWebSocketComposable {
  cleanup: () => void;
  connect: () => Promise<void>;
  connectionAttempts: Ref<number>;
  disconnect: () => void;
  isConnected: ComputedRef<boolean>;
  isConnecting: ComputedRef<boolean>;
  lastError: Ref<string | undefined>;
  onRequest: (handler: MessageHandler) => void;
  onNotification: (handler: NotificationHandler) => void;
  onConnection: (handler: ConnectionHandler) => void;
  removeRequestHandler: () => void;
  removeNotificationHandler: () => void;
  removeConnectionHandler: () => void;
  sendResponse: (response: WalletBridgeResponse) => void;
  sendWalletEvent: (eventName: string, eventData: unknown) => void;
  setupWalletEventListeners: () => void;
  cleanupWalletEventListeners: () => void;
}

export function useWalletBridgeWebSocket(): WalletBridgeWebSocketComposable {
  const ws = ref<WebSocket | null>(null);
  const isConnected = ref<boolean>(false);
  const isConnecting = ref<boolean>(false);
  const connectionAttempts = ref<number>(0);
  const maxRetries = 5;
  const retryDelay = 500;
  const intentionalDisconnect = ref<boolean>(false);
  const lastError = ref<string>();
  const preventReconnect = ref<boolean>(false);

  const messageHandlers = new Map<WalletBridgeEventName, (...args: any[]) => void>();

  // Store references to provider event listeners for cleanup
  const providerEventListeners = new Map<string, (...args: any[]) => void>();

  const sendResponse = (response: WalletBridgeResponse): void => {
    const wsInstance = get(ws);
    if (wsInstance?.readyState === WebSocket.OPEN) {
      wsInstance.send(JSON.stringify(response));
    }
    else {
      logger.error('Cannot send response: WebSocket not connected');
    }
  };

  const handleMessage = (rawMessage: unknown): void => {
    try {
      const message = validateWalletBridgeMessage(rawMessage);
      logger.debug('Received WebSocket message:', message);

      if (isWalletBridgeNotification(message)) {
        const notificationHandler = messageHandlers.get('notification') as NotificationHandler | undefined;
        if (notificationHandler) {
          notificationHandler(message);
        }

        // Special handling for notifications
        if (message.type === 'close_tab') {
          logger.info('Received close_tab notification, attempting to close browser tab');
          try {
            window.close();
          }
          catch (error) {
            logger.error('Failed to close tab:', error);
          }
        }
        else if (message.type === 'reconnected') {
          logger.info('Received reconnected notification, preventing automatic reconnection');
          set(preventReconnect, true);
        }
        return;
      }

      // Handle RPC requests
      if (isWalletBridgeRequest(message)) {
        const requestHandler = messageHandlers.get('request') as MessageHandler | undefined;
        if (requestHandler) {
          requestHandler(message);
        }
        else {
          logger.warn('No message handler registered for requests');

          // Send error response
          sendResponse({
            error: {
              code: -32601,
              message: 'Method not found',
            },
            id: message.id,
            jsonrpc: '2.0',
          });
        }
      }
    }
    catch (error) {
      logger.error('Failed to handle WebSocket message:', error);
      // Optionally send error response if we can extract ID
      if (typeof rawMessage === 'object' && rawMessage && 'id' in rawMessage) {
        sendResponse({
          error: {
            code: -32700,
            message: 'Parse error',
          },
          id: String(rawMessage.id),
          jsonrpc: '2.0',
        });
      }
    }
  };

  const getWebSocketUrl = (): string => {
    // Get the current window location to determine the HTTP port
    const currentPort = window.location.port;
    if (currentPort) {
      // WebSocket server runs on HTTP port + 1
      const wsPort = Number.parseInt(currentPort) + 1;
      return `ws://localhost:${wsPort}/wallet-bridge`;
    }

    // Fallback to default if no port in URL (shouldn't happen for wallet bridge)
    const basePort = 40011; // port + 1 from the default bridge port
    return `ws://localhost:${basePort}/wallet-bridge`;
  };

  const scheduleRetry = (retryCount: number): void => {
    if (retryCount < maxRetries && !get(preventReconnect)) {
      setTimeout(() => {
        connect(retryCount + 1).catch((error) => {
          logger.error('Failed to reconnect:', error);
        });
      }, retryDelay);
    }
  };

  const disconnect = (): void => {
    if (ws.value) {
      set(intentionalDisconnect, true);
      ws.value.close();
      set(ws, null);
      set(isConnected, false);
    }
  };

  async function connect(retryCount = 0): Promise<void> {
    if (ws.value?.readyState === WebSocket.OPEN) {
      return;
    }

    if (retryCount >= maxRetries) {
      logger.error('Max WebSocket connection attempts reached');
      set(isConnecting, false);
      return;
    }

    // Set connecting state when starting connection attempt
    set(isConnecting, true);

    try {
      const wsUrl = getWebSocketUrl();
      logger.info(`Attempting to connect to WebSocket: ${wsUrl}`);

      const websocket = new WebSocket(wsUrl);

      websocket.onopen = (): void => {
        set(ws, websocket);
        set(isConnected, true);
        set(isConnecting, false);
        set(connectionAttempts, 0);
        set(lastError, undefined); // Clear any previous errors

        logger.info('WebSocket connected to Electron app');
      };

      websocket.onmessage = (event): void => {
        try {
          const rawMessage = JSON.parse(event.data) as unknown;
          handleMessage(rawMessage);
        }
        catch (error) {
          logger.error('Failed to parse WebSocket message:', error);
        }
      };

      websocket.onclose = (): void => {
        set(ws, null);
        set(isConnected, false);
        logger.info('WebSocket disconnected');

        // Only retry if this wasn't an intentional disconnect and reconnection is not prevented
        if (!get(intentionalDisconnect) && !get(preventReconnect)) {
          scheduleRetry(retryCount);
        }
        else {
          // Reset the flag for future connections
          set(intentionalDisconnect, false);
          set(isConnecting, false);
        }
      };

      websocket.onerror = (error): void => {
        const errorMessage = `WebSocket connection error (attempt ${retryCount + 1}/${maxRetries})`;
        logger.error(errorMessage, error);
        set(lastError, errorMessage);
        set(ws, null);
        set(isConnected, false);

        // Attempt to reconnect after delay if not prevented
        if (!get(preventReconnect)) {
          scheduleRetry(retryCount);
        }
        else {
          set(isConnecting, false);
        }
      };
    }
    catch (error) {
      const errorMessage = `Failed to create WebSocket connection: ${String(error)}`;
      logger.error(errorMessage);
      set(lastError, errorMessage);
      if (!get(preventReconnect)) {
        scheduleRetry(retryCount);
      }
      else {
        set(isConnecting, false);
      }
    }
  }

  const onRequest = (handler: MessageHandler): void => {
    messageHandlers.set('request', handler);
  };

  const onNotification = (handler: NotificationHandler): void => {
    messageHandlers.set('notification', handler);
  };

  const onConnection = (handler: ConnectionHandler): void => {
    messageHandlers.set('connection', handler);
  };

  const removeRequestHandler = (): void => {
    messageHandlers.delete('request');
  };

  const removeNotificationHandler = (): void => {
    messageHandlers.delete('notification');
  };

  const removeConnectionHandler = (): void => {
    messageHandlers.delete('connection');
  };

  // Auto-connect when component is mounted
  const isReady = computed<boolean>(() => get(isConnected));
  const isConnectingComputed = computed<boolean>(() => get(isConnecting));

  // Function to send wallet events via WebSocket notification
  const sendWalletEvent = (eventName: string, eventData: unknown): void => {
    if (get(isConnected)) {
      const message = {
        eventData,
        eventName,
        type: 'wallet_event' as const,
      };

      const wsInstance = get(ws);
      if (wsInstance?.readyState === WebSocket.OPEN) {
        wsInstance.send(JSON.stringify(message));
        logger.debug(`Sent wallet event: ${eventName}`, eventData);
      }
    }
  };

  // Setup wallet provider event listeners
  const setupWalletEventListeners = (): void => {
    const provider: EIP1193Provider | undefined = window.ethereum;

    if (!provider || !provider.on) {
      logger.warn('No wallet provider found or provider does not support event listeners');
      return;
    }

    // Skip if listeners are already set up
    if (providerEventListeners.size > 0) {
      return;
    }

    // Define event listeners
    const accountsChangedListener = (accounts: string[]): void => {
      logger.debug('Wallet accounts changed:', accounts);
      sendWalletEvent('accountsChanged', accounts);
    };

    const chainChangedListener = (chainId: string): void => {
      logger.debug('Wallet chain changed:', chainId);
      sendWalletEvent('chainChanged', chainId);
    };

    const connectListener = (connectInfo: { chainId: string }): void => {
      logger.debug('Wallet connected:', connectInfo);
      sendWalletEvent('connect', connectInfo);
    };

    const disconnectListener = (error: { code: number; message: string }): void => {
      logger.debug('Wallet disconnected:', error);
      sendWalletEvent('disconnect', error);
    };

    // Add event listeners
    provider.on('accountsChanged', accountsChangedListener);
    provider.on('chainChanged', chainChangedListener);
    provider.on('connect', connectListener);
    provider.on('disconnect', disconnectListener);

    // Store listeners for cleanup
    providerEventListeners.set('accountsChanged', accountsChangedListener);
    providerEventListeners.set('chainChanged', chainChangedListener);
    providerEventListeners.set('connect', connectListener);
    providerEventListeners.set('disconnect', disconnectListener);

    logger.info('Wallet provider event listeners set up');
  };

  // Cleanup wallet event listeners
  const cleanupWalletEventListeners = (): void => {
    const provider: EIP1193Provider | undefined = window.ethereum;

    if (provider?.removeListener) {
      for (const [eventName, listener] of providerEventListeners) {
        provider.removeListener(eventName as keyof EIP1193ProviderEvents, listener);
      }
      providerEventListeners.clear();
      logger.info('Wallet provider event listeners cleaned up');
    }
  };

  // Cleanup on unmount
  const cleanup = (): void => {
    cleanupWalletEventListeners();
    disconnect();
    messageHandlers.clear();
  };

  return {
    cleanup,
    cleanupWalletEventListeners,
    connect,
    connectionAttempts,
    disconnect,
    isConnected: isReady,
    isConnecting: isConnectingComputed,
    lastError,
    onConnection,
    onNotification,
    onRequest,
    removeConnectionHandler,
    removeNotificationHandler,
    removeRequestHandler,
    sendResponse,
    sendWalletEvent,
    setupWalletEventListeners,
  };
}
