import type { Ref } from 'vue';
import type { EIP1193Provider } from '@/types';
import { createSharedComposable } from '@vueuse/core';
import { BrowserProvider, getAddress } from 'ethers';
import { useInterop } from '@/composables/electron-interop';
import { logger } from '@/utils/logging';
import { supportedNetworks } from '../wallet-connect/use-wallet-connect';
import { useUnifiedProviders } from '../wallet-providers/use-unified-providers';
import { useWalletProxy } from './use-wallet-proxy';

interface UseInjectedWalletReturn {
  connected: Ref<boolean>;
  connectedAddress: Ref<string | undefined>;
  connectedChainId: Ref<number | undefined>;
  isConnecting: Ref<boolean>;
  connectToSelectedProvider: () => Promise<void>;
  disconnect: () => Promise<void>;
  getBrowserProvider: () => BrowserProvider;
  switchNetwork: (chainId: bigint) => Promise<void>;
}

function _useInjectedWallet(): UseInjectedWalletReturn {
  const connected = ref<boolean>(false);
  const connectedAddress = ref<string>();
  const connectedChainId = ref<number>();
  const isConnecting = ref<boolean>(false);

  let injectedProvider: EIP1193Provider | undefined;

  // Provider store for enhanced provider detection and selection
  const providerStore = useUnifiedProviders();

  // Define event handlers as part of the composable scope (maintain same references)
  const handleAccountsChanged = (accounts: string[]): void => {
    logger.debug(`Injected provider accounts changed: ${accounts.length} account(s)`);
    if (accounts.length > 0) {
      set(connectedAddress, getAddress(accounts[0]));
      set(connected, true);
    }
    else {
      set(connected, false);
      set(connectedAddress, undefined);
    }
  };

  const handleChainChanged = (chainId: string): void => {
    const newChainId = parseInt(chainId, 16);
    logger.debug('Injected provider changed chain to', newChainId);
    set(connectedChainId, newChainId);
  };

  const handleConnect = (connectInfo: { chainId: string }): void => {
    const newChainId = parseInt(connectInfo.chainId, 16);
    logger.debug(`Injected provider connected to chain: ${newChainId}`);
    set(connected, true);
    set(connectedChainId, newChainId);
  };

  const handleDisconnect = (): void => {
    logger.debug('Injected provider disconnected');
    set(connected, false);
    set(connectedAddress, undefined);
    set(connectedChainId, undefined);
  };

  const handleError = (error: any): void => {
    logger.error('Injected provider error:', error);
    // On WebSocket errors, disconnect the wallet
    set(connected, false);
    set(connectedAddress, undefined);
    set(connectedChainId, undefined);
  };

  const { isPackaged } = useInterop();
  const { disconnectProxy, startConnectionHealthCheck, stopConnectionHealthCheck } = useWalletProxy();

  // Remove event listeners from the injected provider
  const removeProviderEventListeners = (provider: EIP1193Provider): void => {
    logger.debug('Removing injected wallet event listeners from provider');
    if (provider.removeListener) {
      provider.removeListener('accountsChanged', handleAccountsChanged);
      provider.removeListener('chainChanged', handleChainChanged);
      provider.removeListener('connect', handleConnect);
      provider.removeListener('disconnect', handleDisconnect);
      provider.removeListener('error', handleError);
    }
    else {
      logger.warn('Provider has no removeListener method');
    }
  };

  // Connect to injected provider (request accounts)
  const connectInjectedProvider = async (): Promise<void> => {
    if (!injectedProvider) {
      throw new Error('Injected provider not initialized');
    }

    set(isConnecting, true);

    try {
      logger.debug('Requesting accounts from injected provider');
      const accounts = await injectedProvider.request<string[]>({ method: 'eth_requestAccounts' });

      if (accounts.length > 0) {
        set(connectedAddress, getAddress(accounts[0]));
        set(connected, true);
        logger.debug('Injected provider connected to account successfully');
      }
      else {
        logger.warn('No accounts returned from injected provider');
      }
    }
    catch (error) {
      logger.error('Failed to connect injected provider:', error);
      throw error;
    }
    finally {
      set(isConnecting, false);
    }
  };

  // Add event listeners to the injected provider
  const addProviderEventListeners = (provider: EIP1193Provider): void => {
    logger.debug('Adding injected wallet event listeners to provider');

    provider.on?.('accountsChanged', handleAccountsChanged);
    provider.on?.('chainChanged', handleChainChanged);
    provider.on?.('connect', handleConnect);
    provider.on?.('disconnect', handleDisconnect);
    provider.on?.('error', handleError);
  };

  // Connect to the selected provider (called after selection)
  async function connectToSelectedProvider(): Promise<void> {
    const selectedProvider = get(providerStore.selectedProvider);
    if (!selectedProvider) {
      throw new Error('No provider selected');
    }

    logger.debug('Connecting to selected provider:', selectedProvider.info.name);

    // Always use the provider from the unified provider store
    const selectedEthereumProvider = selectedProvider.provider;

    // Clean up previous provider if different
    if (injectedProvider && injectedProvider !== selectedEthereumProvider) {
      removeProviderEventListeners(injectedProvider);
    }

    injectedProvider = selectedEthereumProvider;
    logger.debug(`Using provider from unified store: ${selectedProvider.info.name} (source: ${selectedProvider.source})`);

    // Always remove existing listeners first to prevent duplicates
    removeProviderEventListeners(injectedProvider);

    // Add event listeners
    addProviderEventListeners(injectedProvider);

    // Start health check if packaged
    if (isPackaged) {
      startConnectionHealthCheck(
        () => injectedProvider !== undefined && get(connected),
        () => {
          set(connected, false);
          set(connectedAddress, undefined);
          set(connectedChainId, undefined);
        },
      );
    }

    // CRITICAL: NOW request accounts - only after provider selection
    logger.debug('Provider setup complete, requesting accounts...');
    await connectInjectedProvider();
  }

  async function sendDisconnectToWallet(): Promise<void> {
    if (!injectedProvider) {
      return;
    }

    try {
      // Try to revoke permissions if supported
      await injectedProvider.request({
        method: 'wallet_revokePermissions',
        params: [{ eth_accounts: {} }],
      });
    }
    catch (error: any) {
      // wallet_revokePermissions is not widely supported
      logger.debug('wallet_revokePermissions not supported:', error.message);
      try {
        if ('disconnect' in injectedProvider && typeof injectedProvider.disconnect === 'function') {
          await injectedProvider.disconnect();
        }
      }
      catch (error: any) {
        logger.debug('disconnect failed:', error.message);
      }
    }
  }

  const disconnect = async (): Promise<void> => {
    stopConnectionHealthCheck();

    if (injectedProvider) {
      await sendDisconnectToWallet();

      try {
        // Remove event listeners to prevent memory leaks
        removeProviderEventListeners(injectedProvider);

        // Only disable wallet bridge if packaged
        if (isPackaged) {
          await disconnectProxy();
        }
        injectedProvider = undefined;
      }
      catch (error) {
        logger.error('Failed to disconnect injected provider:', error);
      }
    }

    // Reset state
    set(connected, false);
    set(connectedAddress, undefined);
    set(connectedChainId, undefined);
  };

  const getBrowserProvider = (): BrowserProvider => {
    if (!injectedProvider) {
      throw new Error('Injected provider not initialized');
    }
    return new BrowserProvider(injectedProvider);
  };

  const switchNetwork = async (chainId: bigint): Promise<void> => {
    if (injectedProvider) {
      try {
        await injectedProvider.request({
          method: 'wallet_switchEthereumChain',
          params: [{ chainId: `0x${chainId.toString(16)}` }],
        });

        const newChainId = await injectedProvider.request<string>({ method: 'eth_chainId' });
        set(connectedChainId, parseInt(newChainId, 16));
      }
      catch (error: any) {
        // If the chain doesn't exist, try to add it
        if (error.code === 4902) {
          const network = supportedNetworks.find(item => BigInt(item.id) === chainId);
          if (network) {
            await injectedProvider.request({
              method: 'wallet_addEthereumChain',
              params: [{
                blockExplorerUrls: network.blockExplorers?.default ? [network.blockExplorers.default.url] : [],
                chainId: `0x${chainId.toString(16)}`,
                chainName: network.name,
                nativeCurrency: network.nativeCurrency,
                rpcUrls: network.rpcUrls?.http || [],
              }],
            });
          }
        }
        else {
          throw error;
        }
      }
    }
  };

  return {
    connected,
    connectedAddress,
    connectedChainId,
    connectToSelectedProvider,
    disconnect,
    getBrowserProvider,
    isConnecting,
    switchNetwork,
  };
}

// Export as shared composable to ensure single instance across app
export const useInjectedWallet = createSharedComposable(_useInjectedWallet);
