import { BRIDGE_NOTIFICATION_TYPES } from '@shared/proxy/constants';
import { get, isDefined, set } from '@vueuse/core';
import { ref, type Ref } from 'vue';
import { useBridgeMessageHandlers } from '@/modules/onchain/wallet-bridge/use-bridge-message-handlers';
import { logger } from '@/utils/logging';
import {
  isWalletBridgeNotification,
  isWalletBridgeRequest,
  validateWalletBridgeMessage,
  type WalletBridgeNotification,
  type WalletBridgeRequest,
  type WalletBridgeResponse,
} from './types';

export interface WalletProxyClientComposable {
  cleanup: () => void;
  connect: () => Promise<void>;
  disconnect: () => void;
  isConnected: Readonly<Ref<boolean>>;
  isConnecting: Readonly<Ref<boolean>>;
  lastError: Ref<string | undefined>;
  onTakeOver: (callback: () => void) => void;
}

// Configuration constants
const WEBSOCKET_CONFIG = {
  DEFAULT_BASE_PORT: 40011, // port + 1 from the default bridge port
  MAX_RETRIES: 5,
  RETRY_DELAY: 500,
} as const;

export function useWalletProxyClient(): WalletProxyClientComposable {
  const ws = ref<WebSocket>();
  const isConnected = ref<boolean>(false);
  const isConnecting = ref<boolean>(false);
  const intentionalDisconnect = ref<boolean>(false);
  const lastError = ref<string>();
  const preventReconnect = ref<boolean>(false);
  const onTakeOverCallback = ref<() => void>();

  const { cleanupWalletEventForwarding, handleRequest, setupWalletEventForwarding } = useBridgeMessageHandlers(sendMessage);

  const sendResponse = (response: WalletBridgeResponse): void => {
    const wsInstance = get(ws);
    if (wsInstance?.readyState === WebSocket.OPEN) {
      wsInstance.send(JSON.stringify(response));
    }
    else {
      logger.error('Cannot send response: WebSocket not connected');
    }
  };

  function handleBridgeNotification(notification: WalletBridgeNotification): void {
    // Special handling for notifications
    if (notification.type === BRIDGE_NOTIFICATION_TYPES.CLOSE_TAB) {
      logger.info('Received close_tab notification, attempting to close browser tab');
      try {
        window.close();
      }
      catch (error) {
        logger.error('Failed to close tab:', error);
      }
    }
    else if (notification.type === BRIDGE_NOTIFICATION_TYPES.RECONNECTED) {
      logger.info('Received reconnected notification, preventing automatic reconnection');
      set(preventReconnect, true);
      if (isDefined(onTakeOverCallback)) {
        get(onTakeOverCallback)();
      }
    }
  }

  function handleWalletBridgeRequest(message: WalletBridgeRequest): void {
    handleRequest(message).then((response) => {
      sendResponse(response);
    }).catch((error) => {
      sendResponse({
        error: {
          code: -32601,
          message: error.message || 'Internal error',
        },
        id: message.id,
        jsonrpc: '2.0',
      });
    });
  }

  const handleMessage = (rawMessage: unknown): void => {
    try {
      const message = validateWalletBridgeMessage(rawMessage);
      logger.debug('Received WebSocket message:', message);

      if (isWalletBridgeNotification(message)) {
        handleBridgeNotification(message);
        return;
      }

      // Handle RPC requests
      if (isWalletBridgeRequest(message)) {
        handleWalletBridgeRequest(message);
      }
    }
    catch (error) {
      logger.error('Failed to handle WebSocket message:', error);
      // Optionally send error response if we can extract ID
      if (!(typeof rawMessage === 'object' && rawMessage && 'id' in rawMessage)) {
        return;
      }
      sendResponse({
        error: {
          code: -32700,
          message: 'Parse error',
        },
        id: String(rawMessage.id),
        jsonrpc: '2.0',
      });
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
    return `ws://localhost:${WEBSOCKET_CONFIG.DEFAULT_BASE_PORT}/wallet-bridge`;
  };

  const scheduleRetry = (retryCount: number): void => {
    if (retryCount < WEBSOCKET_CONFIG.MAX_RETRIES && !get(preventReconnect)) {
      setTimeout(() => {
        connect(retryCount + 1).catch((error) => {
          logger.error('Failed to reconnect:', error);
        });
      }, WEBSOCKET_CONFIG.RETRY_DELAY);
    }
  };

  const disconnect = (): void => {
    if (!ws.value) {
      return;
    }
    set(intentionalDisconnect, true);
    ws.value.close();
    set(ws, undefined);
    set(isConnected, false);
  };

  async function connect(retryCount = 0): Promise<void> {
    if (ws.value?.readyState === WebSocket.OPEN) {
      return;
    }

    if (retryCount >= WEBSOCKET_CONFIG.MAX_RETRIES) {
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
        set(lastError, undefined);

        setupWalletEventForwarding();
        logger.info('WebSocket connected to rotki app');
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
        logger.info('WebSocket disconnected');
        set(ws, undefined);
        set(isConnected, false);

        cleanupWalletEventForwarding();

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
        const errorMessage = `WebSocket connection error (attempt ${retryCount + 1}/${WEBSOCKET_CONFIG.MAX_RETRIES})`;
        logger.error(errorMessage, error);
        set(lastError, errorMessage);
        set(ws, undefined);
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

  // Create message handler with WebSocket sending capability
  function sendMessage(message: any): void {
    const wsInstance = get(ws);
    if (wsInstance?.readyState === WebSocket.OPEN) {
      wsInstance.send(JSON.stringify(message));
    }
  }

  function onTakeOver(callback: () => void): void {
    set(onTakeOverCallback, callback);
  }

  const cleanup = (): void => {
    cleanupWalletEventForwarding();
    disconnect();
    set(onTakeOverCallback, undefined);
  };

  return {
    cleanup,
    connect,
    disconnect,
    isConnected: readonly(isConnected),
    isConnecting: readonly(isConnecting),
    lastError,
    onTakeOver,
  };
}
