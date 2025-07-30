import type { BrowserProvider, TransactionResponse } from 'ethers';
import type {
  GasFeeEstimation,
  PrepareERC20TransferResponse,
  PrepareNativeTransferResponse,
  TransactionParams,
} from '@/modules/onchain/types';
import { useInterop } from '@/composables/electron-interop';
import { useSupportedChains } from '@/composables/info/chains';
import { useWalletHelper } from '@/modules/onchain/use-wallet-helper';
import { logger } from '@/utils/logging';
import { useTradeApi } from './send/use-trade-api';
import {
  handleTransactionError,
  prepareTransactionPayload,
  validateTransactionRequirements,
} from './transaction-helpers';
import { useTransactionManager } from './use-transaction-manager';
import { useInjectedWallet } from './wallet-bridge/use-injected-wallet';
import { useWalletProxy } from './wallet-bridge/use-wallet-proxy';
import { supportedNetworks, useWalletConnect } from './wallet-connect/use-wallet-connect';
import { calculateGasFee, WALLET_ERRORS, WALLET_MODES, type WalletMode } from './wallet-constants';
import { useUnifiedProviders } from './wallet-providers/use-unified-providers';

export { type WalletMode } from './wallet-constants';

export const useWalletStore = defineStore('wallet', () => {
  // Core wallet state - centralized instead of delegated
  const preparing = ref<boolean>(false);
  const waitingForWalletConfirmation = ref<boolean>(false);
  const walletMode = ref<WalletMode>(WALLET_MODES.LOCAL_BRIDGE);

  // Consolidated connection state (no more delegation)
  const connected = ref<boolean>(false);
  const connectedAddress = ref<string>();
  const connectedChainId = ref<number>();
  const supportedChainIds = ref<string[]>([]);

  // Initialize composables for both wallet modes
  const walletConnect = useWalletConnect();
  const injectedWallet = useInjectedWallet();
  const walletProxy = useWalletProxy();
  const unifiedProviders = useUnifiedProviders();
  const { isPackaged } = useInterop();

  // Transaction management
  const transactionManager = useTransactionManager();
  const { recentTransactions, updateTransactionStatus } = transactionManager;

  const { getChainFromChainId, getChainIdFromNamespace } = useWalletHelper();
  const { prepareERC20Transfer, prepareNativeTransfer } = useTradeApi();
  const { getEvmChainName } = useSupportedChains();

  // Computed properties
  const isWalletConnect = computed<boolean>(() => get(walletMode) === WALLET_MODES.WALLET_CONNECT);

  // Sync centralized state with active wallet composable
  const syncWalletState = (): void => {
    if (get(walletMode) === WALLET_MODES.WALLET_CONNECT) {
      // Sync from WalletConnect
      set(connected, get(walletConnect.connected));
      set(connectedAddress, get(walletConnect.connectedAddress));
      set(connectedChainId, get(walletConnect.connectedChainId));
      set(supportedChainIds, get(walletConnect.supportedChainIds));
    }
    else {
      // Sync from Local Bridge
      set(connected, get(injectedWallet.connected));
      set(connectedAddress, get(injectedWallet.connectedAddress));
      set(connectedChainId, get(injectedWallet.connectedChainId));
      set(supportedChainIds, []); // Local bridge doesn't have supported chain IDs
    }
  };

  const supportedChainsIdForConnectedAccount = computed<number[]>(() => {
    const chainIds = get(supportedChainIds);
    if (chainIds.length === 0 || get(walletMode) === WALLET_MODES.LOCAL_BRIDGE) {
      // For local bridge or when no supported chains, return all supported networks
      return supportedNetworks.map(network => Number(network.id));
    }
    return chainIds.map(item => getChainIdFromNamespace(item));
  });

  const supportedChainsForConnectedAccount = computed<string[]>(() => get(supportedChainsIdForConnectedAccount).map(item => getChainFromChainId(item)));

  const getBrowserProvider = (): BrowserProvider => {
    if (get(walletMode) === WALLET_MODES.LOCAL_BRIDGE) {
      return injectedWallet.getBrowserProvider();
    }
    return walletConnect.getBrowserProvider();
  };

  const connect = async (): Promise<void> => {
    if (get(walletMode) === WALLET_MODES.LOCAL_BRIDGE) {
      try {
        // Setup bridge if in packaged mode
        if (get(isPackaged)) {
          await walletProxy.setupProxy();
        }

        const providerSelected = await unifiedProviders.checkIfSelectedProvider();

        if (!providerSelected) {
          await unifiedProviders.detectProviders();
          const providers = get(unifiedProviders.availableProviders);

          if (providers.length === 0) {
            throw new Error(WALLET_ERRORS.NO_PROVIDERS);
          }
          else if (providers.length === 1) {
            const provider = providers[0];
            await unifiedProviders.selectProvider(provider.info.uuid);
            await injectedWallet.connectToSelectedProvider();
          }
          else {
            set(unifiedProviders.showProviderSelection, true);
          }
        }
        else {
          await injectedWallet.connectToSelectedProvider();
        }
      }
      catch (error) {
        logger.error(WALLET_ERRORS.CONNECTION_FAILED, error);
        throw error;
      }
    }
    else {
      await walletConnect.connect();
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
    if (get(walletMode) === WALLET_MODES.LOCAL_BRIDGE) {
      await injectedWallet.disconnect();
      unifiedProviders.clearProvider();
    }
    else {
      await walletConnect.disconnect();
    }
    resetState();
  };

  const switchNetwork = async (chainId: bigint): Promise<void> => {
    if (get(walletMode) === WALLET_MODES.LOCAL_BRIDGE) {
      await injectedWallet.switchNetwork(chainId);
    }
    else {
      await walletConnect.switchNetwork(chainId);
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
      // Check connection (universal provider is handled internally)
      await walletConnect.checkWalletConnection();
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

  // Watch for changes in wallet mode and active wallet state
  watch(walletMode, async (walletMode, previousWalletMode) => {
    if (walletMode !== previousWalletMode) {
      await disconnect();
      resetState();
    }
    syncWalletState();
  }, { immediate: true });

  // Watch WalletConnect state changes
  watch([walletConnect.connected, walletConnect.connectedAddress, walletConnect.connectedChainId, walletConnect.supportedChainIds], () => {
    if (get(walletMode) === WALLET_MODES.WALLET_CONNECT) {
      syncWalletState();
    }
  });

  // Watch Local Bridge state changes
  watch([injectedWallet.connected, injectedWallet.connectedAddress, injectedWallet.connectedChainId], () => {
    if (get(walletMode) === WALLET_MODES.LOCAL_BRIDGE) {
      syncWalletState();
    }
  });

  return {
    connect,
    connected,
    connectedAddress,
    connectedChainId,
    disconnect,
    getGasFeeForChain,
    isWalletConnect,
    preparing: logicOr(preparing, injectedWallet.isConnecting),
    recentTransactions,
    sendTransaction,
    supportedChainsForConnectedAccount,
    switchNetwork,
    waitingForWalletConfirmation,
    walletMode,
  };
});
