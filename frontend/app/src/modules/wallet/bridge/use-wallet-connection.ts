import type { Ref } from 'vue';
import type { EIP1193Provider } from '@/types';
import { set } from '@vueuse/shared';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { getAddress } from '../viem-client';

interface UseWalletConnectionReturn {
  cleanupProviderListeners: () => void;
  clearConnectionState: () => void;
  clearProvider: () => void;
  connectedAddress: Readonly<Ref<string | undefined>>;
  connectedChainId: Readonly<Ref<number | undefined>>;
  connectionError: Readonly<Ref<string | undefined>>;
  connectToProvider: (provider: EIP1193Provider) => Promise<void>;
  disconnectFromProvider: (provider?: EIP1193Provider) => Promise<void>;
  handleConnectionError: (error: unknown, context: string) => string;
  isConnecting: Readonly<Ref<boolean>>;
  resetError: () => void;
  setupProvider: (provider: EIP1193Provider) => Promise<void>;
}

export function useWalletConnection(): UseWalletConnectionReturn {
  const connectedAddress = ref<string>();
  const connectedChainId = ref<number>();
  const connectionError = ref<string>();
  const isConnecting = shallowRef<boolean>(false);

  let currentProvider: EIP1193Provider | undefined;
  let accountsChangedListener: ((accounts: string[]) => void) | undefined;
  let chainChangedListener: ((chainId: string) => void) | undefined;

  const setConnectedAddress = (value: string | undefined = undefined): void => {
    set(connectedAddress, value ? getAddress(value) : value);
  };

  const clearConnectionState = (): void => {
    setConnectedAddress();
    set(connectedChainId, undefined);
    set(connectionError, undefined);
  };

  const handleConnectionError = (error: unknown, context: string): string => {
    const errorMessage = error instanceof Object && 'message' in error ? getErrorMessage(error) : `Failed to ${context}`;
    logger.error(`Error ${context}:`, error);
    set(connectionError, errorMessage);
    return errorMessage;
  };

  const resetError = (): void => {
    set(connectionError, undefined);
  };

  const handleAccountsChanged = (accounts: string[]): void => {
    if (accounts.length > 0) {
      setConnectedAddress(accounts[0]);
    }
    else {
      setConnectedAddress();
    }
  };

  const handleChainChanged = (chainId: string): void => {
    set(connectedChainId, parseInt(chainId, 16));
  };

  /**
   * Subscribes to the provider, then reads its current state once.
   *
   * @remarks
   * Subscribing alone leaves the app blank until the wallet next changes something, so the first
   * read has to be made rather than waited for. It throws when the wallet is not connected yet,
   * which is the ordinary case and not worth reporting.
   */
  const setupProviderListeners = async (provider: EIP1193Provider): Promise<void> => {
    if (!provider.on) {
      return;
    }

    accountsChangedListener = handleAccountsChanged;
    chainChangedListener = handleChainChanged;

    provider.on('accountsChanged', accountsChangedListener);
    provider.on('chainChanged', chainChangedListener);
    logger.info('Set up event listeners for provider');

    try {
      const accounts = await provider.request<string[]>({ method: 'eth_accounts' });
      if (accounts && accounts.length > 0) {
        setConnectedAddress(accounts[0]);
        logger.debug('Retrieved current account from provider:', accounts[0]);
      }

      const chainId = await provider.request<string>({ method: 'eth_chainId' });
      if (chainId) {
        set(connectedChainId, parseInt(chainId, 16));
        logger.debug('Retrieved current chain from provider:', chainId);
      }
    }
    catch (error) {
      logger.debug('Failed to query provider state during setup:', error);
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

      const accounts = await provider.request<string[]>({ method: 'eth_requestAccounts' });
      if (accounts.length > 0) {
        setConnectedAddress(accounts[0]);

        const chainId = await provider.request<string>({ method: 'eth_chainId' });
        set(connectedChainId, parseInt(chainId, 16));

        logger.info('Wallet connected successfully:', accounts[0]);
      }
      else {
        throw new Error('No accounts returned from wallet.');
      }
    }
    catch (error: unknown) {
      handleConnectionError(error, 'connect wallet');
      clearConnectionState();
      throw error;
    }
    finally {
      set(isConnecting, false);
    }
  };

  /**
   * Both disconnect paths are optional in EIP-1193, so each is attempted and each failure is
   * logged rather than raised: a wallet supporting neither is a wallet the user has still
   * disconnected from, as far as this app is concerned.
   */
  const disconnectFromProvider = async (provider?: EIP1193Provider): Promise<void> => {
    if (provider) {
      if (provider.disconnect) {
        try {
          await provider.disconnect();
        }
        catch (error) {
          logger.debug('Wallet disconnect method not supported or failed:', error);
        }
      }

      try {
        await provider.request({
          method: 'wallet_revokePermissions',
          params: [{ eth_accounts: {} }],
        });
      }
      catch (error) {
        logger.debug('wallet_revokePermissions not supported:', error);
      }
    }

    clearConnectionState();
    logger.info('Wallet disconnected');
  };

  const setupProvider = async (provider: EIP1193Provider): Promise<void> => {
    if (currentProvider && currentProvider !== provider) {
      cleanupProviderListeners();
    }

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
