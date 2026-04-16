import type { BrowserProvider, TransactionResponse } from 'ethers';
import type {
  GasFeeEstimation,
  PrepareERC20TransferResponse,
  PrepareNativeTransferResponse,
  TransactionParams,
} from '@/modules/wallet/types';
import { assert } from '@rotki/common';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import { useWalletHelper } from '@/modules/wallet/use-wallet-helper';
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

// Lazy backend types
type WalletConnectInstance = ReturnType<typeof import('./use-wallet-connect').useWalletConnect>;

type InjectedWalletInstance = ReturnType<typeof import('./bridge/use-injected-wallet').useInjectedWallet>;

export const useWalletStore = defineStore('wallet', () => {
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
  const { recentTransactions, updateTransactionStatus } = transactionManager;

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

  const getBrowserProvider = (): BrowserProvider => {
    if (get(walletMode) === WALLET_MODES.LOCAL_BRIDGE) {
      assert(injectedWalletInstance, 'Injected wallet not initialized');
      return injectedWalletInstance.getBrowserProvider();
    }
    assert(walletConnectInstance, 'WalletConnect not initialized');
    return walletConnectInstance.getBrowserProvider();
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
      const provider = getBrowserProvider();
      const address = get(connectedAddress);

      if (!address) {
        return {
          gasFee: '0',
          maxAmount: '0',
        };
      }

      const [feeData, balance] = await Promise.all([
        provider.getFeeData(),
        provider.getBalance(address),
      ]);

      const gasPrice = feeData.gasPrice ?? feeData.maxFeePerGas ?? 0n;

      return calculateGasFee(gasPrice, balance);
    }
    catch (error) {
      logger.error(WALLET_ERRORS.GAS_ESTIMATION_FAILED, error);
      throw error;
    }
  };

  const executeTransaction = async (backendPayload: PrepareERC20TransferResponse | PrepareNativeTransferResponse): Promise<TransactionResponse> => {
    set(waitingForWalletConfirmation, true);
    const provider = getBrowserProvider();
    const signer = await provider.getSigner();
    const tx = await signer.sendTransaction({
      ...backendPayload,
      type: 0,
    });
    set(waitingForWalletConfirmation, false);
    return tx;
  };

  const sendTransaction = async (params: TransactionParams): Promise<TransactionResponse> => {
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

      const tx = await executeTransaction(backendPayload);
      await transactionManager.handleTransactionSuccess(
        tx,
        chainId,
        params,
        get(connectedAddress),
        getChainFromChainId,
      );

      return tx;
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

  // Watch for changes in wallet mode
  watch(walletMode, async (walletMode, previousWalletMode) => {
    if (walletMode !== previousWalletMode) {
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
    recentTransactions,
    sendTransaction,
    supportedChainsForConnectedAccount,
    switchNetwork,
    waitingForWalletConfirmation,
    walletMode,
  };
});
