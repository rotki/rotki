import type { Ref } from 'vue';
import type { EIP1193EventName, EIP1193Provider, EIP1193ProviderEvents } from '@/types';
import { assert } from '@rotki/common';
import { createSharedComposable } from '@vueuse/core';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import { useUnifiedProviders } from '../providers/use-unified-providers';
import { createViemWalletClient, getAddress, type ViemWalletClient } from '../viem-client';
import { useWalletProxy } from './use-wallet-proxy';

interface UseInjectedWalletReturn {
  connected: Ref<boolean>;
  connectedAddress: Ref<string | undefined>;
  connectedChainId: Ref<number | undefined>;
  isConnecting: Ref<boolean>;
  connectToSelectedProvider: () => Promise<void>;
  disconnect: () => Promise<void>;
  getWalletClient: () => ViemWalletClient;
  switchNetwork: (chainId: bigint) => Promise<void>;
}

function _useInjectedWallet(): UseInjectedWalletReturn {
  const connected = ref<boolean>(false);
  const connectedAddress = ref<string>();
  const connectedChainId = ref<number>();
  const isConnecting = ref<boolean>(false);

  let injectedProvider: EIP1193Provider | undefined;

  const providerStore = useUnifiedProviders();

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

  /**
   * Visits every provider event this composable subscribes to, with the handler bound to it.
   *
   * @remarks
   * The single place the pairing is written down. Subscribing and unsubscribing both go through
   * here, so they cannot drift apart and both necessarily pass the same function reference, which
   * is what `removeListener` matches on. Adding an event means adding one line here.
   *
   * @param apply - run once per event; `on` and `removeListener` are what get passed in.
   */
  function eachProviderEvent(
    apply: <K extends EIP1193EventName>(event: K, handler: (...args: EIP1193ProviderEvents[K]) => void) => void,
  ): void {
    apply('accountsChanged', handleAccountsChanged);
    apply('chainChanged', handleChainChanged);
    apply('connect', handleConnect);
    apply('disconnect', handleDisconnect);
    apply('error', handleError);
  }

  const removeProviderEventListeners = (provider: EIP1193Provider): void => {
    logger.debug('Removing injected wallet event listeners from provider');
    if (!provider.removeListener) {
      logger.warn('Provider has no removeListener method');
      return;
    }

    eachProviderEvent((event, handler) => provider.removeListener?.(event, handler));
  };

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
        await updateChainId();
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

  const addProviderEventListeners = (provider: EIP1193Provider): void => {
    logger.debug('Adding injected wallet event listeners to provider');

    eachProviderEvent((event, handler) => provider.on?.(event, handler));
  };

  /**
   * Wires up the provider the user picked, then asks it for accounts.
   *
   * @remarks
   * The account request has to come last. Asking before the provider is wired prompts the user
   * against whichever wallet happened to be active, which is not the one they chose. Listeners are
   * removed before being added because a provider can be selected again without changing, and the
   * second pass would otherwise leave two of each.
   */
  async function connectToSelectedProvider(): Promise<void> {
    const selectedProvider = get(providerStore.selectedProvider);
    if (!selectedProvider) {
      throw new Error('No provider selected');
    }

    logger.debug('Connecting to selected provider:', selectedProvider.info.name);

    const selectedEthereumProvider = selectedProvider.provider;

    if (injectedProvider && injectedProvider !== selectedEthereumProvider) {
      removeProviderEventListeners(injectedProvider);
    }

    injectedProvider = selectedEthereumProvider;
    logger.debug(`Using provider from unified store: ${selectedProvider.info.name} (source: ${selectedProvider.source})`);

    removeProviderEventListeners(injectedProvider);

    addProviderEventListeners(injectedProvider);

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

    logger.debug('Provider setup complete, requesting accounts...');
    await connectInjectedProvider();
  }

  /**
   * Tells the wallet the session is over, as far as it is willing to be told.
   *
   * @remarks
   * Neither method is universal: `wallet_revokePermissions` is the one that actually makes the
   * wallet forget the approval, `disconnect` is the older fallback, and a wallet supporting
   * neither leaves the user to disconnect from its own UI. Every failure here is logged and
   * swallowed, since local disconnection must proceed either way.
   */
  async function sendDisconnectToWallet(): Promise<void> {
    if (!injectedProvider) {
      return;
    }

    try {
      await injectedProvider.request({
        method: 'wallet_revokePermissions',
        params: [{ eth_accounts: {} }],
      });
    }
    catch (error: unknown) {
      logger.debug('wallet_revokePermissions not supported:', getErrorMessage(error));
      try {
        if ('disconnect' in injectedProvider && typeof injectedProvider.disconnect === 'function') {
          await injectedProvider.disconnect();
        }
      }
      catch (error: unknown) {
        logger.debug('disconnect failed:', getErrorMessage(error));
      }
    }
  }

  const disconnect = async (): Promise<void> => {
    stopConnectionHealthCheck();

    if (injectedProvider) {
      await sendDisconnectToWallet();

      try {
        removeProviderEventListeners(injectedProvider);

        if (isPackaged) {
          await disconnectProxy();
        }
        injectedProvider = undefined;
      }
      catch (error) {
        logger.error('Failed to disconnect injected provider:', error);
      }
    }

    set(connected, false);
    set(connectedAddress, undefined);
    set(connectedChainId, undefined);
  };

  const getWalletClient = (): ViemWalletClient => {
    if (!injectedProvider) {
      throw new Error('Injected provider not initialized');
    }
    return createViemWalletClient(injectedProvider);
  };

  async function updateChainId(): Promise<void> {
    assert(injectedProvider, 'Injected provider not initialized');
    const newChainId = await injectedProvider.request<string>({ method: 'eth_chainId' });
    set(connectedChainId, parseInt(newChainId, 16));
  }

  const switchNetwork = async (chainId: bigint): Promise<void> => {
    if (injectedProvider) {
      try {
        await injectedProvider.request({
          method: 'wallet_switchEthereumChain',
          params: [{ chainId: `0x${chainId.toString(16)}` }],
        });

        await updateChainId();
      }
      catch (error: unknown) {
        // If the chain doesn't exist, try to add it
        if (error instanceof Object && 'code' in error && error.code === 4902) {
          const { getWalletNetwork } = await import('../chains-viem');
          const network = getWalletNetwork(chainId);
          if (!network)
            throw error;

          await injectedProvider.request({
            method: 'wallet_addEthereumChain',
            params: [{
              blockExplorerUrls: network.blockExplorers?.default ? [network.blockExplorers.default.url] : [],
              chainId: `0x${chainId.toString(16)}`,
              chainName: network.name,
              nativeCurrency: network.nativeCurrency,
              rpcUrls: network.rpcUrls.default.http,
            }],
          });
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
    getWalletClient,
    isConnecting,
    switchNetwork,
  };
}

// Export as shared composable to ensure single instance across app
export const useInjectedWallet = createSharedComposable(_useInjectedWallet);
