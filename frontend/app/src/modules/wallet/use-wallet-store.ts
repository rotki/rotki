import type {
  GasFeeEstimation,
  PrepareERC20TransferResponse,
  PrepareNativeTransferResponse,
  RecentTransaction,
  TransactionParams,
} from '@/modules/wallet/types';
import { assert } from '@rotki/common';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import { useWalletHelper } from '@/modules/wallet/use-wallet-helper';
import { getAddress, type Hash, isHex, type ViemWalletClient } from '@/modules/wallet/viem-client';
import { useWalletProxy } from './bridge/use-wallet-proxy';
import { calculateGasFee, SUPPORTED_WALLET_CHAIN_IDS, WALLET_ERRORS, WALLET_MODES, type WalletMode } from './constants';
import { useUnifiedProviders } from './providers/use-unified-providers';
import { useTradeApi } from './send/use-trade-api';
import {
  handleTransactionError,
  prepareTransactionPayload,
  validateTransactionRequirements,
} from './transaction-helpers';
import { useTransactionManager } from './use-transaction-manager';

export { type WalletMode } from './constants';

const STORE_ID = 'wallet';

// Lazy backend types
type WalletConnectInstance = ReturnType<typeof import('./use-wallet-connect').useWalletConnect>;

type InjectedWalletInstance = ReturnType<typeof import('./bridge/use-injected-wallet').useInjectedWallet>;

export const useWalletStore = defineStore(STORE_ID, () => {
  // Core wallet state - centralized instead of delegated
  const preparing = ref<boolean>(false);
  const waitingForWalletConfirmation = ref<boolean>(false);
  const walletMode = ref<WalletMode>(WALLET_MODES.LOCAL_BRIDGE);
  const isDisconnecting = ref<boolean>(false);

  // Consolidated connection state (no more delegation)
  const connected = ref<boolean>(false);
  const connectedAddress = ref<string>();
  const connectedChainId = ref<number>();
  const supportedChainIds = ref<string[]>([]);

  // Local ref to mirror injectedWallet.isConnecting (since injected wallet may not be loaded)
  const isConnecting = ref<boolean>(false);

  // Lightweight composables (no ethers/WC dependencies)
  const walletProxy = useWalletProxy();
  const unifiedProviders = useUnifiedProviders();
  const { isPackaged } = useInterop();

  // Transaction management
  const transactionManager = useTransactionManager();
  const { recentTransactions, reset: resetTransactions, updateTransactionStatus } = transactionManager;

  const { getChainFromChainId, getChainIdFromNamespace } = useWalletHelper();
  const { prepareERC20Transfer, prepareNativeTransfer } = useTradeApi();
  const { getEvmChainName } = useSupportedChains();

  // Lazy backend instances — loaded on first use
  let walletConnectInstance: WalletConnectInstance | undefined;
  let injectedWalletInstance: InjectedWalletInstance | undefined;

  // Computed properties
  const isWalletConnect = computed<boolean>(() => get(walletMode) === WALLET_MODES.WALLET_CONNECT);

  // Sync centralized state with active wallet composable
  const syncWalletState = (): void => {
    if (get(walletMode) === WALLET_MODES.WALLET_CONNECT) {
      if (!walletConnectInstance)
        return;
      set(connected, get(walletConnectInstance.connected));
      set(connectedAddress, get(walletConnectInstance.connectedAddress));
      set(connectedChainId, get(walletConnectInstance.connectedChainId));
      set(supportedChainIds, get(walletConnectInstance.supportedChainIds));
    }
    else {
      if (!injectedWalletInstance)
        return;
      set(connected, get(injectedWalletInstance.connected));
      set(connectedAddress, get(injectedWalletInstance.connectedAddress));
      set(connectedChainId, get(injectedWalletInstance.connectedChainId));
      set(supportedChainIds, []);
    }
  };

  async function getWalletConnect(): Promise<WalletConnectInstance> {
    if (!walletConnectInstance) {
      const { useWalletConnect } = await import('./use-wallet-connect');
      walletConnectInstance = useWalletConnect();
      // Set up state sync watcher (moved from eager watcher)
      watch(
        [
          walletConnectInstance.connected,
          walletConnectInstance.connectedAddress,
          walletConnectInstance.connectedChainId,
          walletConnectInstance.supportedChainIds,
        ],
        () => {
          if (get(walletMode) === WALLET_MODES.WALLET_CONNECT)
            syncWalletState();
        },
      );
    }
    return walletConnectInstance;
  }

  async function getInjectedWallet(): Promise<InjectedWalletInstance> {
    if (!injectedWalletInstance) {
      const { useInjectedWallet } = await import('./bridge/use-injected-wallet');
      injectedWalletInstance = useInjectedWallet();
      // Mirror isConnecting into local ref
      watch(injectedWalletInstance.isConnecting, (v) => {
        set(isConnecting, v);
      });
      // Set up state sync watcher (moved from eager watcher)
      watch(
        [
          injectedWalletInstance.connected,
          injectedWalletInstance.connectedAddress,
          injectedWalletInstance.connectedChainId,
        ],
        () => {
          if (get(walletMode) === WALLET_MODES.LOCAL_BRIDGE)
            syncWalletState();
        },
      );
    }
    return injectedWalletInstance;
  }

  const supportedChainsIdForConnectedAccount = computed<number[]>(() => {
    const chainIds = get(supportedChainIds);
    if (chainIds.length === 0 || get(walletMode) === WALLET_MODES.LOCAL_BRIDGE) {
      return [...SUPPORTED_WALLET_CHAIN_IDS];
    }
    return chainIds.map(item => getChainIdFromNamespace(item));
  });

  const supportedChainsForConnectedAccount = computed<string[]>(() => get(supportedChainsIdForConnectedAccount).map(item => getChainFromChainId(item)));

  const getWalletClient = (): ViemWalletClient => {
    if (get(walletMode) === WALLET_MODES.LOCAL_BRIDGE) {
      assert(injectedWalletInstance, 'Injected wallet not initialized');
      return injectedWalletInstance.getWalletClient();
    }
    assert(walletConnectInstance, 'WalletConnect not initialized');
    return walletConnectInstance.getWalletClient();
  };

  const connect = async (): Promise<void> => {
    if (get(walletMode) === WALLET_MODES.LOCAL_BRIDGE) {
      try {
        // Setup bridge if in packaged mode
        if (get(isPackaged)) {
          await walletProxy.setupProxy();
        }

        const providerSelected = await unifiedProviders.checkIfSelectedProvider();
        const iw = await getInjectedWallet();

        if (!providerSelected) {
          await unifiedProviders.detectProviders();
          const providers = get(unifiedProviders.availableProviders);

          if (providers.length === 0) {
            throw new Error(WALLET_ERRORS.NO_PROVIDERS);
          }
          else if (providers.length === 1) {
            const provider = providers[0];
            await unifiedProviders.selectProvider(provider.info.uuid);
            await iw.connectToSelectedProvider();
          }
          else {
            set(unifiedProviders.showProviderSelection, true);
          }
        }
        else {
          await iw.connectToSelectedProvider();
        }
      }
      catch (error) {
        logger.error(WALLET_ERRORS.CONNECTION_FAILED, error);
        throw error;
      }
    }
    else {
      const wc = await getWalletConnect();
      await wc.connect();
    }
  };

  const resetState = (): void => {
    logger.debug('Resetting wallet state');
    set(preparing, false);
    set(waitingForWalletConfirmation, false);
    // Clear centralized connection state
    set(connected, false);
    set(connectedAddress, undefined);
    set(connectedChainId, undefined);
    set(supportedChainIds, []);
  };

  // Called by the store reset plugin on logout. `$patch` cannot clear the recent
  // transactions since they are exposed as a getter, so they are reset here.
  const reset = (): void => {
    resetState();
    resetTransactions();
  };

  const disconnect = async (): Promise<void> => {
    set(isDisconnecting, true);
    try {
      if (get(walletMode) === WALLET_MODES.LOCAL_BRIDGE) {
        if (injectedWalletInstance) {
          await injectedWalletInstance.disconnect();
        }
        unifiedProviders.clearProvider();
      }
      else {
        if (walletConnectInstance) {
          await walletConnectInstance.disconnect();
        }
      }
      resetState();
    }
    finally {
      set(isDisconnecting, false);
    }
  };

  const switchNetwork = async (chainId: bigint): Promise<void> => {
    if (get(walletMode) === WALLET_MODES.LOCAL_BRIDGE) {
      const iw = await getInjectedWallet();
      await iw.switchNetwork(chainId);
    }
    else {
      const wc = await getWalletConnect();
      await wc.switchNetwork(chainId);
    }
  };

  const getGasFeeForChain = async (): Promise<GasFeeEstimation> => {
    try {
      const client = getWalletClient();
      const address = get(connectedAddress);

      if (!address) {
        return {
          gasFee: '0',
          maxAmount: '0',
        };
      }

      const [gasPrice, balance] = await Promise.all([
        client.getGasPrice(),
        client.getBalance({ address: getAddress(address) }),
      ]);

      return calculateGasFee(gasPrice, balance);
    }
    catch (error) {
      logger.error(WALLET_ERRORS.GAS_ESTIMATION_FAILED, error);
      throw error;
    }
  };

  const executeTransaction = async (client: ViemWalletClient, backendPayload: PrepareERC20TransferResponse | PrepareNativeTransferResponse): Promise<Hash> => {
    set(waitingForWalletConfirmation, true);
    const data = 'data' in backendPayload ? backendPayload.data : '0x';
    if (!isHex(data)) {
      throw new Error('Invalid transaction data');
    }
    const hash = await client.sendTransaction({
      account: getAddress(backendPayload.from),
      chain: null,
      data,
      nonce: backendPayload.nonce,
      to: getAddress(backendPayload.to),
      type: 'legacy',
      value: backendPayload.value,
    });
    set(waitingForWalletConfirmation, false);
    return hash;
  };

  const sendTransaction = async (params: TransactionParams): Promise<Hash> => {
    // Check WalletConnect connection if in WalletConnect mode
    if (get(walletMode) === WALLET_MODES.WALLET_CONNECT) {
      const wc = await getWalletConnect();
      await wc.checkWalletConnection();
    }

    try {
      const { chainId, evmChain, fromAddress } = validateTransactionRequirements({
        connectedAddress: get(connectedAddress),
        connectedChainId: get(connectedChainId),
        getEvmChainName,
        params,
      });

      set(preparing, true);
      const backendPayload = await prepareTransactionPayload(
        params,
        fromAddress,
        evmChain,
        {
          prepareERC20Transfer,
          prepareNativeTransfer,
        },
      );
      set(preparing, false);

      const client = getWalletClient();
      const hash = await executeTransaction(client, backendPayload);
      await transactionManager.handleTransactionSuccess(
        client,
        hash,
        chainId,
        params,
        get(connectedAddress),
        getChainFromChainId,
      );

      return hash;
    }
    catch (error) {
      handleTransactionError(error, {
        setPreparing: (value: boolean) => set(preparing, value),
        setWaitingForWalletConfirmation: (value: boolean) => set(waitingForWalletConfirmation, value),
        updateTransactionStatus,
      });
      throw error;
    }
  };

  // Watch for changes in wallet mode. The immediate run has no previous mode and nothing is
  // connected yet, so disconnecting there would only clear the remembered provider.
  watch(walletMode, async (walletMode, previousWalletMode) => {
    if (previousWalletMode !== undefined && walletMode !== previousWalletMode) {
      await disconnect();
      resetState();
    }
    syncWalletState();
  }, { immediate: true });

  return {
    connect,
    connected,
    connectedAddress,
    connectedChainId,
    disconnect,
    getGasFeeForChain,
    isDisconnecting,
    isWalletConnect,
    preparing: logicOr(preparing, isConnecting),
    recentTransactions: computed<RecentTransaction[]>(() => get(recentTransactions)),
    reset,
    sendTransaction,
    supportedChainsForConnectedAccount,
    switchNetwork,
    waitingForWalletConfirmation,
    walletMode,
  };
});

/**
 * Disconnects the wallet only when the store already exists.
 *
 * A session that never opened the wallet has nothing to disconnect, and calling
 * `useWalletStore()` would build the whole wallet graph (bridge proxy, providers, transaction
 * manager) just to tear it down. The auth flows use this so the login screen no longer
 * instantiates the store.
 */
export async function disconnectWalletIfActive(): Promise<void> {
  const pinia = getActivePinia();
  if (!pinia || !Object.hasOwn(pinia.state.value, STORE_ID))
    return;

  await useWalletStore().disconnect();
}
