import type { EIP1193Provider, EIP1193ProviderEvents, EIP6963ProviderDetail } from '@/types';
import { BRIDGE_NOTIFICATION_TYPES, WALLET_EVENT_TYPES } from '@shared/proxy/constants';
import { get, set } from '@vueuse/core';
import { computed, type ComputedRef, ref, type Ref } from 'vue';
import { useBridgeMessageHandlers } from '@/modules/onchain/wallet-bridge/use-bridge-message-handlers';
import { logger } from '@/utils/logging';
import { useUnifiedProviders } from '../wallet-providers/use-unified-providers';
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
  connectionAttempts: Ref<number>;
  disconnect: () => void;
  isConnected: ComputedRef<boolean>;
  isConnecting: ComputedRef<boolean>;
  lastError: Ref<string | undefined>;
  sendWalletEvent: (eventName: string, eventData: unknown) => void;
  setupWalletEventListeners: () => void;
  cleanupWalletEventListeners: () => void;
  onTakeOver: (callback: () => void) => void;
  // EIP-6963 Provider Detection
  getAvailableProviders: (options?: any) => Promise<EIP6963ProviderDetail[]>;
  getSelectedProvider: () => EIP1193Provider | undefined;
  hasSelectedProvider: Ref<boolean>;
  isDetectingProviders: Ref<boolean>;
  selectProvider: (uuid: string) => Promise<boolean>;
}

export function useWalletProxyClient(): WalletProxyClientComposable {
  const ws = ref<WebSocket>();
  const isConnected = ref<boolean>(false);
  const isConnecting = ref<boolean>(false);
  const connectionAttempts = ref<number>(0);
  const maxRetries = 5;
  const retryDelay = 500;
  const intentionalDisconnect = ref<boolean>(false);
  const lastError = ref<string>();
  const preventReconnect = ref<boolean>(false);
  const providerEventListeners = new Map<string, (...args: any[]) => void>();
  const onTakeOverCallback = ref<() => void>();

  const { handleRequest } = useBridgeMessageHandlers();

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
      set(ws, undefined);
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
        set(ws, undefined);
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

  const isReady = computed<boolean>(() => get(isConnected));
  const isConnectingComputed = computed<boolean>(() => get(isConnecting));

  const {
    activeProvider,
    detectProviders: getAvailableProviders,
    hasSelectedProvider,
    isDetecting: isDetectingProviders,
    selectProvider,
  } = useUnifiedProviders();

  const getSelectedProvider = (): EIP1193Provider | undefined => get(activeProvider);

  function onTakeOver(callback: () => void): void {
    set(onTakeOverCallback, callback);
  }

  const sendWalletEvent = (eventName: string, eventData: unknown): void => {
    if (get(isConnected)) {
      const message = {
        eventData,
        eventName,
        type: BRIDGE_NOTIFICATION_TYPES.WALLET_EVENT,
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
    const provider = getSelectedProvider();

    if (!provider) {
      logger.warn('No wallet provider selected');
    }

    if (!provider?.on) {
      logger.warn('No wallet provider found or provider does not support event listeners');
      return;
    }

    // Skip if listeners are already set up
    if (providerEventListeners.size > 0) {
      return;
    }

    const accountsChangedListener = (accounts: string[]): void => {
      logger.debug('Wallet accounts changed:', accounts);
      sendWalletEvent(WALLET_EVENT_TYPES.ACCOUNTS_CHANGED, accounts);
    };

    const chainChangedListener = (chainId: string): void => {
      logger.debug('Wallet chain changed:', chainId);
      sendWalletEvent(WALLET_EVENT_TYPES.CHAIN_CHANGED, chainId);
    };

    const connectListener = (connectInfo: { chainId: string }): void => {
      logger.debug('Wallet connected:', connectInfo);
      sendWalletEvent(WALLET_EVENT_TYPES.CONNECT, connectInfo);
    };

    const disconnectListener = (error: { code: number; message: string }): void => {
      logger.debug('Wallet disconnected:', error);
      sendWalletEvent(WALLET_EVENT_TYPES.DISCONNECT, error);
    };

    // Add event listeners
    provider.on(WALLET_EVENT_TYPES.ACCOUNTS_CHANGED, accountsChangedListener);
    provider.on(WALLET_EVENT_TYPES.CHAIN_CHANGED, chainChangedListener);
    provider.on(WALLET_EVENT_TYPES.CONNECT, connectListener);
    provider.on(WALLET_EVENT_TYPES.DISCONNECT, disconnectListener);

    // Store listeners for cleanup
    providerEventListeners.set(WALLET_EVENT_TYPES.ACCOUNTS_CHANGED, accountsChangedListener);
    providerEventListeners.set(WALLET_EVENT_TYPES.CHAIN_CHANGED, chainChangedListener);
    providerEventListeners.set(WALLET_EVENT_TYPES.CONNECT, connectListener);
    providerEventListeners.set(WALLET_EVENT_TYPES.DISCONNECT, disconnectListener);

    logger.info('Wallet provider event listeners set up');
  };

  const cleanupWalletEventListeners = (): void => {
    const provider = getSelectedProvider();

    if (provider?.removeListener) {
      for (const [eventName, listener] of providerEventListeners) {
        provider.removeListener(eventName as keyof EIP1193ProviderEvents, listener);
      }
      providerEventListeners.clear();
      logger.info('Wallet provider event listeners cleaned up');
    }
  };

  const cleanup = (): void => {
    cleanupWalletEventListeners();
    disconnect();
    set(onTakeOverCallback, undefined);
  };

  return {
    cleanup,
    cleanupWalletEventListeners,
    connect,
    connectionAttempts,
    disconnect,
    getAvailableProviders,
    getSelectedProvider,
    hasSelectedProvider,
    isConnected: isReady,
    isConnecting: isConnectingComputed,
    isDetectingProviders,
    lastError,
    onTakeOver,
    selectProvider: async (uuid: string) => selectProvider(uuid),
    sendWalletEvent,
    setupWalletEventListeners,
  };
}
