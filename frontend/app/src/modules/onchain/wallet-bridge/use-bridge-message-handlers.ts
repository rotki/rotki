import type { WalletBridgeRequest, WalletBridgeResponse } from './types';
import type { EIP1193Provider } from '@/types';
import { BRIDGE_ERROR_CODES, ROTKI_RPC_METHODS, ROTKI_RPC_RESPONSES } from '@shared/proxy/constants';
import { get, promiseTimeout } from '@vueuse/core';
import { useBridgeLogging } from '@/modules/onchain/wallet-bridge/use-bridge-logging';
import { logger } from '@/utils/logging';
import { useUnifiedProviders } from '../wallet-providers/use-unified-providers';

export interface BridgeMessageHandlersComposable {
  handleRequest: (message: WalletBridgeRequest) => Promise<WalletBridgeResponse>;
}

export function useBridgeMessageHandlers(): BridgeMessageHandlersComposable {
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

  // Track whether we've made a successful eth_requestAccounts call for the current provider
  let hasSuccessfulAccountsRequest = false;

  // Reset the flag when provider changes
  onProviderChanged(() => {
    hasSuccessfulAccountsRequest = false;
    logger.debug('[Bridge] Provider changed, reset accounts request flag');
  });

  const handleCustomRequest = async (message: WalletBridgeRequest): Promise<WalletBridgeResponse | null> => {
    switch (message.method) {
      case ROTKI_RPC_METHODS.PING: {
        // Custom ping method for bridge readiness check - doesn't require RPC provider
        addLog('Received bridge ping - responding with pong', 'info');
        return {
          id: message.id,
          jsonrpc: '2.0',
          result: ROTKI_RPC_RESPONSES.PONG,
        };
      }

      case ROTKI_RPC_METHODS.GET_AVAILABLE_PROVIDERS: {
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
        return {
          id: message.id,
          jsonrpc: '2.0',
          result: serializedProviders,
        };
      }

      case ROTKI_RPC_METHODS.GET_SELECTED_PROVIDER: {
        const provider = getSelectedProvider();
        const metadata = get(selectedProviderMetadata);
        const uuid = get(selectedProviderUuid);

        if (provider && metadata && uuid) {
          const providerDetail = {
            info: metadata,
            provider: {},
          };
          addLog(`The app asked for the selected provider: ${metadata.name}`, 'info');
          return {
            id: message.id,
            jsonrpc: '2.0',
            result: providerDetail,
          };
        }

        addLog('The app asked for the selected provider: no provider', 'info');
        return {
          id: message.id,
          jsonrpc: '2.0',
          result: null,
        };
      }

      case ROTKI_RPC_METHODS.SELECT_PROVIDER: {
        const [uuid] = (message.params as [string]) || [];
        addLog(`The user select the following provider: ${uuid || 'none (clearing selection)'}`, 'info');
        if (uuid === undefined || uuid === null) {
          return {
            error: {
              code: BRIDGE_ERROR_CODES.INVALID_PARAMS,
              message: 'Invalid params: uuid required',
            },
            id: message.id,
            jsonrpc: '2.0',
          };
        }

        const success = await selectProvider(uuid);
        return {
          id: message.id,
          jsonrpc: '2.0',
          result: success,
        };
      }

      default:
        return null; // Not a custom rotki or EIP-6963 method
    }
  };

  const handleStandardRequest = async (message: WalletBridgeRequest): Promise<WalletBridgeResponse> => {
    const provider = getSelectedProvider();

    if (!provider) {
      return {
        error: {
          code: BRIDGE_ERROR_CODES.NO_PROVIDER,
          message: 'No browser wallet provider found',
        },
        id: message.id,
        jsonrpc: '2.0',
      };
    }

    // Helper function to execute the request
    const executeRequest = async (): Promise<unknown> => {
      // Initialize provider on first eth_requestAccounts call
      if (message.method === 'eth_requestAccounts' && !hasSuccessfulAccountsRequest && 'initialize' in provider && typeof provider.initialize === 'function') {
        try {
          logger.debug('[Bridge] Initializing provider before first eth_requestAccounts');
          await provider.initialize();
          logger.debug('[Bridge] Provider initialization successful');
        }
        catch (error) {
          logger.warn('[Bridge] Provider initialization failed, continuing anyway:', error);
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
        logger.debug('[Bridge] eth_requestAccounts succeeded, marking flag');
      }

      return {
        id: message.id,
        jsonrpc: '2.0',
        result,
      };
    }
    catch (error: unknown) {
      const err = error as Error & { code?: number; data?: unknown };

      // Only retry first eth_requestAccounts with 4001 error (proxy initialization issue)
      if (message.method === 'eth_requestAccounts' && err.code === 4001 && !hasSuccessfulAccountsRequest) {
        logger.info('[Bridge] First eth_requestAccounts failed with 4001 (proxy initialization), retrying once...');

        try {
          // Add a small delay before retry to let proxy settle
          await promiseTimeout(500);

          // Retry the request
          const result = await executeRequest();

          // Mark successful on retry
          hasSuccessfulAccountsRequest = true;
          logger.info('[Bridge] eth_requestAccounts retry succeeded');

          return {
            id: message.id,
            jsonrpc: '2.0',
            result,
          };
        }
        catch (retryError: unknown) {
          const retryErr = retryError as Error & { code?: number; data?: unknown };
          logger.error('[Bridge] eth_requestAccounts retry failed:', retryErr);

          // Return the retry error
          return {
            error: {
              code: retryErr.code || BRIDGE_ERROR_CODES.INTERNAL_ERROR,
              data: retryErr.data,
              message: retryErr.message || 'Internal error',
            },
            id: message.id,
            jsonrpc: '2.0',
          };
        }
      }

      // For all other errors, subsequent eth_requestAccounts with 4001, or non-4001 errors
      logger.error('[Bridge] Error handling request:', err);
      return {
        error: {
          code: err.code || BRIDGE_ERROR_CODES.INTERNAL_ERROR,
          data: err.data,
          message: err.message || 'Internal error',
        },
        id: message.id,
        jsonrpc: '2.0',
      };
    }
  };

  const handleRequest = async (message: WalletBridgeRequest): Promise<WalletBridgeResponse> => {
    try {
      // Try custom rotki and EIP-6963 methods first
      const customResponse = await handleCustomRequest(message);
      if (customResponse) {
        return customResponse;
      }

      // Fall back to standard wallet methods
      return await handleStandardRequest(message);
    }
    catch (error: unknown) {
      logger.error('Error handling bridge request:', error);
      const err = error as Error & { code?: number };
      return {
        error: {
          code: err.code || BRIDGE_ERROR_CODES.INTERNAL_ERROR,
          message: err.message || 'Unexpected error occurred',
        },
        id: message.id,
        jsonrpc: '2.0',
      };
    }
  };

  return {
    handleRequest,
  };
}
