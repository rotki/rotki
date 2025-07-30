import type { Ref } from 'vue';
import type { EIP1193Provider } from '@/types';
import { set } from '@vueuse/shared';
import { logger } from '@/utils/logging';

interface UseWalletConnectionReturn {
  cleanupProviderListeners: () => void;
  clearConnectionState: () => void;
  clearProvider: () => void;
  connectedAddress: Readonly<Ref<string | undefined>>;
  connectedChainId: Readonly<Ref<number | undefined>>;
  connectionError: Readonly<Ref<string | undefined>>;
  connectToProvider: (provider: EIP1193Provider) => Promise<void>;
  disconnectFromProvider: (provider?: EIP1193Provider) => Promise<void>;
  handleConnectionError: (error: any, context: string) => string;
  isConnecting: Readonly<Ref<boolean>>;
  resetError: () => void;
  setupProvider: (provider: EIP1193Provider) => Promise<void>;
}

export function useWalletConnection(): UseWalletConnectionReturn {
  const connectedAddress = ref<string>();
  const connectedChainId = ref<number>();
  const connectionError = ref<string>();
  const isConnecting = ref<boolean>(false);

  // Provider management
  let currentProvider: EIP1193Provider | undefined;
  let accountsChangedListener: ((accounts: string[]) => void) | undefined;
  let chainChangedListener: ((chainId: string) => void) | undefined;

  const clearConnectionState = (): void => {
    set(connectedAddress, undefined);
    set(connectedChainId, undefined);
    set(connectionError, undefined);
  };

  const handleConnectionError = (error: any, context: string): string => {
    const errorMessage = 'message' in error ? error.message : `Failed to ${context}`;
    logger.error(`Error ${context}:`, error);
    set(connectionError, errorMessage);
    return errorMessage;
  };

  const resetError = (): void => {
    set(connectionError, undefined);
  };

  const handleAccountsChanged = (accounts: string[]): void => {
    if (accounts.length > 0) {
      set(connectedAddress, accounts[0]);
    }
    else {
      set(connectedAddress, undefined);
    }
  };

  const handleChainChanged = (chainId: string): void => {
    set(connectedChainId, parseInt(chainId, 16));
  };

  const setupProviderListeners = async (provider: EIP1193Provider): Promise<void> => {
    if (!provider.on) {
      return;
    }

    // Store listener references for cleanup
    accountsChangedListener = handleAccountsChanged;
    chainChangedListener = handleChainChanged;

    provider.on('accountsChanged', accountsChangedListener);
    provider.on('chainChanged', chainChangedListener);
    logger.info('Set up event listeners for provider');

    // Immediately query the provider for current state to avoid timing issues
    try {
      // Get current accounts
      const accounts = await provider.request<string[]>({ method: 'eth_accounts' });
      if (accounts && accounts.length > 0) {
        set(connectedAddress, accounts[0]);
        logger.debug('Retrieved current account from provider:', accounts[0]);
      }

      // Get current chain ID
      const chainId = await provider.request<string>({ method: 'eth_chainId' });
      if (chainId) {
        set(connectedChainId, parseInt(chainId, 16));
        logger.debug('Retrieved current chain from provider:', chainId);
      }
    }
    catch (error) {
      logger.debug('Failed to query provider state during setup:', error);
      // This is expected if the wallet is not connected yet
    }
  };

  const cleanupProviderListeners = (): void => {
    if (currentProvider?.removeListener && accountsChangedListener && chainChangedListener) {
      currentProvider.removeListener('accountsChanged', accountsChangedListener);
      currentProvider.removeListener('chainChanged', chainChangedListener);
      logger.info('Cleaned up event listeners for provider');
    }
    currentProvider = undefined;
    accountsChangedListener = undefined;
    chainChangedListener = undefined;
  };

  const connectToProvider = async (provider: EIP1193Provider): Promise<void> => {
    try {
      set(isConnecting, true);
      set(connectionError, undefined);

      if (!provider) {
        throw new Error('No wallet provider found. Please select a wallet provider first.');
      }

      // Request account access
      const accounts = await provider.request<string[]>({ method: 'eth_requestAccounts' });
      if (accounts.length > 0) {
        set(connectedAddress, accounts[0]);

        // Get chain ID after connecting
        const chainId = await provider.request<string>({ method: 'eth_chainId' });
        set(connectedChainId, parseInt(chainId, 16));

        logger.info('Wallet connected successfully:', accounts[0]);
      }
      else {
        throw new Error('No accounts returned from wallet.');
      }
    }
    catch (error: any) {
      handleConnectionError(error, 'connect wallet');
      clearConnectionState();
      throw error;
    }
    finally {
      set(isConnecting, false);
    }
  };

  const disconnectFromProvider = async (provider?: EIP1193Provider): Promise<void> => {
    if (provider) {
      // Some wallets support disconnect method
      if (provider.disconnect) {
        try {
          await provider.disconnect();
        }
        catch (error) {
          // Some wallets don't support disconnect, which is fine
          logger.debug('Wallet disconnect method not supported or failed:', error);
        }
      }

      // For wallets that don't support disconnect, we can request permissions revocation
      // This is not universally supported but works for some wallets
      try {
        await provider.request({
          method: 'wallet_revokePermissions',
          params: [{ eth_accounts: {} }],
        });
      }
      catch (error) {
        // This method is not supported by all wallets
        logger.debug('wallet_revokePermissions not supported:', error);
      }
    }

    // Clear the connected state
    clearConnectionState();
    logger.info('Wallet disconnected');
  };

  const setupProvider = async (provider: EIP1193Provider): Promise<void> => {
    // Clean up old provider listeners
    if (currentProvider && currentProvider !== provider) {
      cleanupProviderListeners();
    }

    // Set up new provider
    currentProvider = provider;
    await setupProviderListeners(provider);
  };

  const clearProvider = (): void => {
    clearConnectionState();
    cleanupProviderListeners();
  };

  return {
    cleanupProviderListeners,
    clearConnectionState,
    clearProvider,
    connectedAddress: readonly(connectedAddress),
    connectedChainId: readonly(connectedChainId),
    connectionError: readonly(connectionError),
    connectToProvider,
    disconnectFromProvider,
    handleConnectionError,
    isConnecting: readonly(isConnecting),
    resetError,
    setupProvider,
  };
}
