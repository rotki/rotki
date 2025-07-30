import type { WalletBridgeRequest, WalletBridgeResponse } from '@shared/wallet-bridge-types';
import type { EIP1193Provider, EIP1193ProviderEvents } from '@/types';
import { BRIDGE_ERROR_CODES, BRIDGE_NOTIFICATION_TYPES, ROTKI_RPC_METHODS, ROTKI_RPC_RESPONSES, WALLET_EVENT_TYPES } from '@shared/proxy/constants';
import { get, promiseTimeout } from '@vueuse/core';
import { useBridgeLogging } from '@/modules/onchain/wallet-bridge/use-bridge-logging';
import { logger } from '@/utils/logging';
import { useUnifiedProviders } from '../wallet-providers/use-unified-providers';

export interface BridgeMessageHandlersComposable {
  handleRequest: (message: WalletBridgeRequest) => Promise<WalletBridgeResponse>;
  setupWalletEventForwarding: () => void;
  cleanupWalletEventForwarding: () => void;
}

// Response creation helpers
function createSuccessResponse(id: string | number, result: unknown): WalletBridgeResponse {
  return {
    id,
    jsonrpc: '2.0',
    result,
  };
}

function createErrorResponse(id: string | number, code: number, message: string, data?: unknown): WalletBridgeResponse {
  return {
    error: {
      code,
      data,
      message,
    },
    id,
    jsonrpc: '2.0',
  };
}

// Configuration constants
const REQUEST_CONFIG = {
  RETRY_DELAY: 500,
} as const;

export function useBridgeMessageHandlers(sendMessage?: (message: any) => void): BridgeMessageHandlersComposable {
  const providerEventListeners = new Map<string, (...args: any[]) => void>();
  let hasSuccessfulAccountsRequest = false;

  const {
    activeProvider,
    detectProviders: getAvailableProviders,
    onProviderChanged,
    selectedProviderMetadata,
    selectedProviderUuid,
    selectProvider,
  } = useUnifiedProviders();

  const getSelectedProvider = (): EIP1193Provider | undefined => get(activeProvider);

  const { addLog } = useBridgeLogging();

  // Reset the flag when provider changes
  onProviderChanged(() => {
    hasSuccessfulAccountsRequest = false;
    logger.debug('Provider changed, reset accounts request flag');
  });

  async function rpcGetAvailableProviders(message: WalletBridgeRequest): Promise<WalletBridgeResponse> {
    // Single async method that detects if needed and returns providers
    const providers = await getAvailableProviders();
    // Serialize providers for bridge - remove circular references from provider objects
    const serializedProviders = providers.map(provider => ({
      info: provider.info,
      isConnected: provider.isConnected,
      lastSeen: provider.lastSeen,
      source: provider.source,
    }));
    addLog(`The app asked for the available providers: ${providers.length}`, 'info');
    return createSuccessResponse(message.id, serializedProviders);
  }

  function rpcGetSelectedProvider(message: WalletBridgeRequest): WalletBridgeResponse {
    const provider = getSelectedProvider();
    const metadata = get(selectedProviderMetadata);
    const uuid = get(selectedProviderUuid);

    if (provider && metadata && uuid) {
      const providerDetail = {
        info: metadata,
        provider: {},
      };
      addLog(`The app asked for the selected provider: ${metadata.name}`, 'info');
      return createSuccessResponse(message.id, providerDetail);
    }

    addLog('The app asked for the selected provider: no provider', 'info');
    return createSuccessResponse(message.id, null);
  }

  async function rpcSelectProvider(message: WalletBridgeRequest): Promise<WalletBridgeResponse> {
    const [uuid] = (message.params as [string]) || [];
    addLog(`The user select the following provider: ${uuid || 'none (clearing selection)'}`, 'info');
    if (uuid === undefined || uuid === null) {
      return createErrorResponse(message.id, BRIDGE_ERROR_CODES.INVALID_PARAMS, 'Invalid params: uuid required');
    }

    const success = await selectProvider(uuid);
    return createSuccessResponse(message.id, success);
  }

  function rpcPing(message: WalletBridgeRequest): WalletBridgeResponse {
    // Custom ping method for bridge readiness check - doesn't require RPC provider
    addLog('Received bridge ping - responding with pong', 'info');
    return createSuccessResponse(message.id, ROTKI_RPC_RESPONSES.PONG);
  }

  const handleRotkiRpcRequest = async (message: WalletBridgeRequest): Promise<WalletBridgeResponse | null> => {
    switch (message.method) {
      case ROTKI_RPC_METHODS.PING: {
        return rpcPing(message);
      }
      case ROTKI_RPC_METHODS.GET_AVAILABLE_PROVIDERS: {
        return rpcGetAvailableProviders(message);
      }
      case ROTKI_RPC_METHODS.GET_SELECTED_PROVIDER: {
        return rpcGetSelectedProvider(message);
      }
      case ROTKI_RPC_METHODS.SELECT_PROVIDER: {
        return rpcSelectProvider(message);
      }
      default:
        return null; // Not a custom rotki or EIP-6963 method
    }
  };

  const handleStandardRpcRequest = async (message: WalletBridgeRequest): Promise<WalletBridgeResponse> => {
    const provider = getSelectedProvider();

    if (!provider) {
      return createErrorResponse(message.id, BRIDGE_ERROR_CODES.NO_PROVIDER, 'No browser wallet provider found');
    }

    // Helper function to execute the request
    const executeRequest = async (): Promise<unknown> => {
      // Initialize provider on first eth_requestAccounts call
      if (message.method === 'eth_requestAccounts' && !hasSuccessfulAccountsRequest && 'initialize' in provider && typeof provider.initialize === 'function') {
        try {
          logger.debug('Initializing provider before first eth_requestAccounts');
          await provider.initialize();
          logger.debug('Provider initialization successful');
        }
        catch (error) {
          logger.warn('Provider initialization failed, continuing anyway:', error);
          // Continue anyway - initialization failure shouldn't block the request
        }
      }

      return provider.request<unknown>({
        method: message.method,
        params: message.params || [],
      });
    };

    try {
      // Try the request
      const result = await executeRequest();

      // Mark successful eth_requestAccounts call
      if (message.method === 'eth_requestAccounts') {
        hasSuccessfulAccountsRequest = true;
        logger.debug('eth_requestAccounts succeeded, marking flag');
      }

      return createSuccessResponse(message.id, result);
    }
    catch (error: unknown) {
      const err = error as Error & { code?: number; data?: unknown };

      // Only retry first eth_requestAccounts with 4001 error (proxy initialization issue)
      if (message.method === 'eth_requestAccounts' && err.code === 4001 && !hasSuccessfulAccountsRequest) {
        logger.info('First eth_requestAccounts failed with 4001 (proxy initialization), retrying once...');

        try {
          // Add a small delay before retry to let proxy settle
          await promiseTimeout(REQUEST_CONFIG.RETRY_DELAY);

          // Retry the request
          const result = await executeRequest();

          // Mark successful on retry
          hasSuccessfulAccountsRequest = true;
          logger.info('eth_requestAccounts retry succeeded');

          return createSuccessResponse(message.id, result);
        }
        catch (retryError: unknown) {
          const retryErr = retryError as Error & { code?: number; data?: unknown };
          logger.error('eth_requestAccounts retry failed:', retryErr);

          // Return the retry error
          return createErrorResponse(
            message.id,
            retryErr.code || BRIDGE_ERROR_CODES.INTERNAL_ERROR,
            retryErr.message || 'Internal error',
            retryErr.data,
          );
        }
      }

      // For all other errors, subsequent eth_requestAccounts with 4001, or non-4001 errors
      logger.error('Error handling request:', err);
      return createErrorResponse(
        message.id,
        err.code || BRIDGE_ERROR_CODES.INTERNAL_ERROR,
        err.message || 'Internal error',
        err.data,
      );
    }
  };

  const handleRequest = async (message: WalletBridgeRequest): Promise<WalletBridgeResponse> => {
    try {
      const rpcResponse = await handleRotkiRpcRequest(message);
      if (rpcResponse) {
        return rpcResponse;
      }

      // Fall back to standard wallet methods
      return await handleStandardRpcRequest(message);
    }
    catch (error: unknown) {
      logger.error('Error handling bridge request:', error);
      const err = error as Error & { code?: number };
      return createErrorResponse(
        message.id,
        err.code || BRIDGE_ERROR_CODES.INTERNAL_ERROR,
        err.message || 'Unexpected error occurred',
      );
    }
  };

  const sendWalletEvent = (eventName: string, eventData: unknown): void => {
    if (sendMessage) {
      const message = {
        eventData,
        eventName,
        type: BRIDGE_NOTIFICATION_TYPES.WALLET_EVENT,
      };
      sendMessage(message);
      logger.debug(`Sent wallet event: ${eventName}`, eventData);
    }
    else {
      logger.warn('Cannot send wallet event: no sendMessage function provided');
    }
  };

  // Helper to create event listener with consistent logging and forwarding
  const createEventListener = (eventType: string, logPrefix: string) => (...args: any[]): void => {
    logger.debug(`${logPrefix}:`, ...args);
    sendWalletEvent(eventType, args.length === 1 ? args[0] : args);
  };

  const setupWalletEventForwarding = (): void => {
    const provider = getSelectedProvider();

    if (!provider) {
      logger.warn('No wallet provider selected');
      return;
    }

    if (!provider?.on) {
      logger.warn('No wallet provider found or provider does not support event listeners');
      return;
    }

    // Skip if listeners are already set up
    if (providerEventListeners.size > 0) {
      return;
    }

    // Create event listeners with consistent pattern
    const eventConfigs = [
      { logPrefix: 'Wallet accounts changed', type: WALLET_EVENT_TYPES.ACCOUNTS_CHANGED },
      { logPrefix: 'Wallet chain changed', type: WALLET_EVENT_TYPES.CHAIN_CHANGED },
      { logPrefix: 'Wallet connected', type: WALLET_EVENT_TYPES.CONNECT },
      { logPrefix: 'Wallet disconnected', type: WALLET_EVENT_TYPES.DISCONNECT },
    ];

    for (const { logPrefix, type } of eventConfigs) {
      const listener = createEventListener(type, logPrefix);
      provider.on(type, listener);
      providerEventListeners.set(type, listener);
    }

    logger.info('Wallet provider event listeners set up');
  };

  const cleanupWalletEventForwarding = (): void => {
    const provider = getSelectedProvider();

    if (!provider?.removeListener) {
      return;
    }
    for (const [eventName, listener] of providerEventListeners) {
      provider.removeListener(eventName as keyof EIP1193ProviderEvents, listener);
    }
    providerEventListeners.clear();
    logger.info('Wallet provider event listeners cleaned up');
  };

  return {
    cleanupWalletEventForwarding,
    handleRequest,
    setupWalletEventForwarding,
  };
}
