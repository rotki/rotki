import type { Ref } from 'vue';
import type { EIP1193Provider } from '@/types';
import { BrowserProvider, getAddress } from 'ethers';
import { useInterop } from '@/composables/electron-interop';
import { logger } from '@/utils/logging';
import { supportedNetworks } from '../wallet-connect/use-wallet-connect';
import { useBridgedWallet } from './use-bridged-wallet';

interface UseInjectedWalletReturn {
  connected: Ref<boolean>;
  connectedAddress: Ref<string | undefined>;
  connectedChainId: Ref<number | undefined>;
  open: () => Promise<void>;
  disconnect: () => Promise<void>;
  getBrowserProvider: () => BrowserProvider;
  switchNetwork: (chainId: bigint) => Promise<void>;
}

export function useInjectedWallet(setPreparing?: (preparing: boolean) => void): UseInjectedWalletReturn {
  const connected = ref<boolean>(false);
  const connectedAddress = ref<string>();
  const connectedChainId = ref<number>();

  let injectedProvider: EIP1193Provider | undefined;

  // Store event handler references for proper cleanup
  const providerEventHandlers: {
    accountsChanged?: (accounts: string[]) => void;
    chainChanged?: (chainId: string) => void;
    connect?: (connectInfo: { chainId: string }) => void;
    disconnect?: () => void;
    error?: (error: any) => void;
  } = {};

  const { isPackaged } = useInterop();
  const { disconnectBridge, setupBridge, startConnectionHealthCheck, stopConnectionHealthCheck } = useBridgedWallet();

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

  // Setup event handlers for the injected provider
  const setupProviderEventHandlers = (): void => {
    providerEventHandlers.accountsChanged = (accounts: string[]): void => {
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

    providerEventHandlers.chainChanged = (chainId: string): void => {
      const newChainId = parseInt(chainId, 16);
      logger.debug('Injected provider changed chain to', newChainId);
      set(connectedChainId, newChainId);
    };

    providerEventHandlers.connect = (connectInfo: { chainId: string }): void => {
      const newChainId = parseInt(connectInfo.chainId, 16);
      logger.debug(`Injected provider connected to chain: ${newChainId}`);
      set(connected, true);
      set(connectedChainId, newChainId);
    };

    providerEventHandlers.disconnect = (): void => {
      logger.debug('Injected provider disconnected');
      set(connected, false);
      set(connectedAddress, undefined);
      set(connectedChainId, undefined);
    };

    providerEventHandlers.error = (error: any): void => {
      logger.error('Injected provider error:', error);
      // On WebSocket errors, disconnect the wallet
      set(connected, false);
      set(connectedAddress, undefined);
      set(connectedChainId, undefined);
    };
  };

  // Add event listeners to the injected provider
  const addProviderEventListeners = (provider: EIP1193Provider): void => {
    if (providerEventHandlers.accountsChanged) {
      provider.on?.('accountsChanged', providerEventHandlers.accountsChanged);
    }
    if (providerEventHandlers.chainChanged) {
      provider.on?.('chainChanged', providerEventHandlers.chainChanged);
    }
    if (providerEventHandlers.connect) {
      provider.on?.('connect', providerEventHandlers.connect);
    }
    if (providerEventHandlers.disconnect) {
      provider.on?.('disconnect', providerEventHandlers.disconnect);
    }
    if (providerEventHandlers.error) {
      provider.on?.('error', providerEventHandlers.error);
    }
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
      injectedProvider = window.ethereum;

      if (!injectedProvider) {
        throw new Error('No injected provider found');
      }

      // Setup event handlers
      setupProviderEventHandlers();

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

  // Remove event listeners from the injected provider
  const removeProviderEventListeners = (provider: EIP1193Provider): void => {
    if (providerEventHandlers.accountsChanged && provider.removeListener) {
      provider.removeListener('accountsChanged', providerEventHandlers.accountsChanged);
    }
    if (providerEventHandlers.chainChanged && provider.removeListener) {
      provider.removeListener('chainChanged', providerEventHandlers.chainChanged);
    }
    if (providerEventHandlers.connect && provider.removeListener) {
      provider.removeListener('connect', providerEventHandlers.connect);
    }
    if (providerEventHandlers.disconnect && provider.removeListener) {
      provider.removeListener('disconnect', providerEventHandlers.disconnect);
    }
    if (providerEventHandlers.error && provider.removeListener) {
      provider.removeListener('error', providerEventHandlers.error);
    }
  };

  // Clear all provider event handler references
  const clearProviderEventHandlers = (): void => {
    providerEventHandlers.accountsChanged = undefined;
    providerEventHandlers.chainChanged = undefined;
    providerEventHandlers.connect = undefined;
    providerEventHandlers.disconnect = undefined;
    providerEventHandlers.error = undefined;
  };

  const open = async (): Promise<void> => {
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

        // Clear handler references
        clearProviderEventHandlers();

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
