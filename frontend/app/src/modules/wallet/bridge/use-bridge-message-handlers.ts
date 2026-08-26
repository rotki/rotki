import type { WalletBridgeRequest, WalletBridgeResponse } from '@shared/wallet-bridge-types';
import type { EIP1193EventName, EIP1193Provider } from '@/types';
import { BRIDGE_ERROR_CODES, BRIDGE_NOTIFICATION_TYPES, ROTKI_RPC_METHODS, ROTKI_RPC_RESPONSES, WALLET_EVENT_TYPES } from '@shared/proxy/constants';
import { defaultWindow, get, promiseTimeout } from '@vueuse/core';
import { type RpcError, toRpcError } from '@/modules/core/api/types/errors';
import { logger } from '@/modules/core/common/logging/logging';
import { useBridgeLogging } from '@/modules/wallet/bridge/use-bridge-logging';
import { useWalletConnectionState } from '@/modules/wallet/bridge/use-wallet-connection-state';
import { useUnifiedProviders } from '../providers/use-unified-providers';

interface BridgeMessageHandlersComposable {
  handleRequest: (message: WalletBridgeRequest) => Promise<WalletBridgeResponse>;
}

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

const REQUEST_CONFIG = {
  RETRY_DELAY: 500,
} as const;

export function useBridgeMessageHandlers(sendMessage?: (message: any) => void): BridgeMessageHandlersComposable {
  const providerEventListeners = new Map<EIP1193EventName, (...args: any[]) => void>();
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
  const { trackAccountsRequest } = useWalletConnectionState();

  onProviderChanged((newProvider, oldProvider) => {
    hasSuccessfulAccountsRequest = false;
    logger.debug('Provider changed, reset accounts request flag');
    cleanupWalletEventForwarding(oldProvider);
    setupWalletEventForwarding(newProvider);
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
    const [firstParam] = message.params ?? [];
    const uuid = typeof firstParam === 'string' && firstParam.length > 0 ? firstParam : undefined;
    addLog(`The user select the following provider: ${uuid ?? 'none (clearing selection)'}`, 'info');
    if (uuid === undefined) {
      return createErrorResponse(message.id, BRIDGE_ERROR_CODES.INVALID_PARAMS, 'Invalid params: uuid required');
    }

    const success = await selectProvider(uuid);
    defaultWindow?.focus();
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

  function errorResponseFor(id: string | number, error: RpcError): WalletBridgeResponse {
    return createErrorResponse(
      id,
      error.code ?? BRIDGE_ERROR_CODES.INTERNAL_ERROR,
      error.message || 'Internal error',
      error.data,
    );
  }

  /**
   * A 4001 on the very first eth_requestAccounts is usually the proxy still initialising rather than a
   * real user rejection, so that single case is worth one retry. Later rejections are taken at face
   * value.
   */
  function shouldRetryAccountsRequest(message: WalletBridgeRequest, error: RpcError): boolean {
    return message.method === 'eth_requestAccounts'
      && error.code === 4001
      && !hasSuccessfulAccountsRequest;
  }

  async function retryAccountsRequest(
    message: WalletBridgeRequest,
    executeRequest: () => Promise<unknown>,
  ): Promise<WalletBridgeResponse> {
    logger.info('First eth_requestAccounts failed with 4001 (proxy initialization), retrying once...');

    try {
      // Add a small delay before retry to let proxy settle
      await promiseTimeout(REQUEST_CONFIG.RETRY_DELAY);
      const result = await trackAccountsRequest(executeRequest());

      hasSuccessfulAccountsRequest = true;
      logger.info('eth_requestAccounts retry succeeded');

      return createSuccessResponse(message.id, result);
    }
    catch (retryError: unknown) {
      const retryErr = toRpcError(retryError);
      logger.error('eth_requestAccounts retry failed:', retryErr);
      return errorResponseFor(message.id, retryErr);
    }
  }

  const handleStandardRpcRequest = async (message: WalletBridgeRequest): Promise<WalletBridgeResponse> => {
    const provider = getSelectedProvider();

    if (!provider) {
      return createErrorResponse(message.id, BRIDGE_ERROR_CODES.NO_PROVIDER, 'No browser wallet provider found');
    }

    /** The provider is initialised lazily, on the first `eth_requestAccounts` and only once. */
    const executeRequest = async (): Promise<unknown> => {
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
        params: message.params ?? [],
      });
    };

    try {
      const result = message.method === 'eth_requestAccounts'
        ? await trackAccountsRequest(executeRequest())
        : await executeRequest();

      if (message.method === 'eth_requestAccounts') {
        hasSuccessfulAccountsRequest = true;
        logger.debug('eth_requestAccounts succeeded, marking flag');
      }

      return createSuccessResponse(message.id, result);
    }
    catch (error: unknown) {
      const err = toRpcError(error);

      if (shouldRetryAccountsRequest(message, err))
        return retryAccountsRequest(message, executeRequest);

      logger.error('Error handling request:', err);
      return errorResponseFor(message.id, err);
    }
  };

  const handleRequest = async (message: WalletBridgeRequest): Promise<WalletBridgeResponse> => {
    try {
      const rpcResponse = await handleRotkiRpcRequest(message);
      if (rpcResponse) {
        return rpcResponse;
      }

      return await handleStandardRpcRequest(message);
    }
    catch (error: unknown) {
      logger.error('Error handling bridge request:', error);
      const err = toRpcError(error);
      return createErrorResponse(
        message.id,
        err.code ?? BRIDGE_ERROR_CODES.INTERNAL_ERROR,
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

  const createEventListener = (eventType: string, logPrefix: string) => (...args: any[]): void => {
    logger.debug(`forwarding: ${logPrefix}:`, ...args);
    sendWalletEvent(eventType, args.length === 1 ? args[0] : args);
  };

  function setupWalletEventForwarding(provider: EIP1193Provider | undefined): void {
    if (!provider) {
      logger.warn('No wallet provider selected');
      return;
    }

    if (!provider?.on) {
      logger.warn('No wallet provider found or provider does not support event listeners');
      return;
    }

    if (providerEventListeners.size > 0) {
      return;
    }

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
  }

  function cleanupWalletEventForwarding(provider: EIP1193Provider | undefined): void {
    if (!provider?.removeListener) {
      return;
    }
    for (const [eventName, listener] of providerEventListeners) {
      provider.removeListener(eventName, listener);
    }
    providerEventListeners.clear();
    logger.info('Wallet provider event listeners cleaned up');
  }

  return {
    handleRequest,
  };
}
