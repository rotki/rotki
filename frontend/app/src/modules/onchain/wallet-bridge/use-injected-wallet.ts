import type { Ref } from 'vue';
import type { EIP1193Provider } from '@/types';
import { createSharedComposable } from '@vueuse/core';
import { BrowserProvider, getAddress } from 'ethers';
import { useInterop } from '@/composables/electron-interop';
import { logger } from '@/utils/logging';
import { supportedNetworks } from '../wallet-connect/use-wallet-connect';
import { useBridgedWallet } from './use-bridged-wallet';

interface UseInjectedWalletReturn {
  connected: Ref<boolean>;
  connectedAddress: Ref<string | undefined>;
  connectedChainId: Ref<number | undefined>;
  open: (setPreparing?: (preparing: boolean) => void) => Promise<void>;
  disconnect: () => Promise<void>;
  getBrowserProvider: () => BrowserProvider;
  switchNetwork: (chainId: bigint) => Promise<void>;
}

function _useInjectedWallet(): UseInjectedWalletReturn {
  const connected = ref<boolean>(false);
  const connectedAddress = ref<string>();
  const connectedChainId = ref<number>();

  let injectedProvider: EIP1193Provider | undefined;

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
  const { disconnectBridge, setupBridge, startConnectionHealthCheck, stopConnectionHealthCheck } = useBridgedWallet();

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

  // Get initial state from provider with retry logic
  const getInitialProviderState = async (provider: EIP1193Provider, retries: number = 30): Promise<void> => {
    try {
      const accounts = await provider.request<string[]>({ method: 'eth_accounts' });
      if (accounts.length > 0) {
        set(connectedAddress, getAddress(accounts[0]));
        set(connected, true);
      }

      const chainId = await provider.request<string>({ method: 'eth_chainId' });
      set(connectedChainId, parseInt(chainId, 16));
    }
    catch (error) {
      if (retries > 0) {
        logger.debug(`Failed to get initial provider state, retrying... (${retries} attempts left)`);
        await new Promise(resolve => setTimeout(resolve, 1000));
        await getInitialProviderState(provider, retries - 1);
      }
      else {
        logger.error('Failed to get initial provider state after retries:', error);
        // Don't throw error, just continue without initial state
      }
    }
  };

  // Initialize injected provider (with optional bridge setup when packaged)
  const initializeInjectedProvider = async (): Promise<void> => {
    if (typeof window === 'undefined') {
      return;
    }

    try {
      // Only setup bridge when packaged, otherwise use direct injected provider
      if (isPackaged) {
        await setupBridge();
      }

      // Get the ethereum provider (either through bridge or directly injected)
      const newProvider = window.ethereum;

      if (!newProvider) {
        throw new Error('No injected provider found');
      }

      // Clean up previous provider if it exists and is different
      if (injectedProvider && injectedProvider !== newProvider) {
        removeProviderEventListeners(injectedProvider);
      }

      injectedProvider = newProvider;

      // Always remove existing listeners first to prevent duplicates
      if (injectedProvider) {
        removeProviderEventListeners(injectedProvider);
      }

      // Add event listeners
      addProviderEventListeners(injectedProvider);

      // Get initial state
      await getInitialProviderState(injectedProvider);

      // Start periodic connection health check only when packaged
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
    }
    catch (error) {
      logger.error('Failed to initialize injected provider:', error);
      throw error;
    }
  };

  const open = async (setPreparing?: (preparing: boolean) => void): Promise<void> => {
    try {
      // Set loading state when bridge setup starts
      setPreparing?.(true);

      // Initialize the injected provider
      await initializeInjectedProvider();
      // Request account connection
      await connectInjectedProvider();
    }
    finally {
      // Clear loading state regardless of success/failure
      setPreparing?.(false);
    }
  };

  const disconnect = async (): Promise<void> => {
    // Stop health check
    stopConnectionHealthCheck();

    if (injectedProvider) {
      try {
        // Remove event listeners to prevent memory leaks
        removeProviderEventListeners(injectedProvider);

        // Only disable wallet bridge if packaged
        if (isPackaged) {
          await disconnectBridge();
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
    disconnect,
    getBrowserProvider,
    open,
    switchNetwork,
  };
}

// Export as shared composable to ensure single instance across app
export const useInjectedWallet = createSharedComposable(_useInjectedWallet);
