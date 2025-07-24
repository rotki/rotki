import type {
  GasFeeEstimation,
  PrepareERC20TransferResponse,
  PrepareNativeTransferResponse,
  RecentTransaction,
  TransactionParams,
} from '@/modules/onchain/types';
import { assert, bigNumberify } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { type BrowserProvider, formatUnits, type TransactionResponse } from 'ethers';
import { useSupportedChains } from '@/composables/info/chains';
import { useWalletConnection } from '@/composables/wallets/use-wallet-connection';
import { useWalletHelper } from '@/modules/onchain/use-wallet-helper';
import { useAssetCacheStore } from '@/store/assets/asset-cache';
import { logger } from '@/utils/logging';
import { useTradeApi } from './send/use-trade-api';
import {
  handleTransactionError,
  prepareTransactionPayload,
  validateTransactionRequirements,
} from './transaction-helpers';
import { useInjectedWallet } from './wallet-bridge/use-injected-wallet';
import { useWalletConnect } from './wallet-connect/use-wallet-connect';

const DEFAULT_GAS_LIMIT = 21000n; // for native transfers

export type WalletMode = 'walletconnect' | 'local-bridge';

export const useWalletStore = defineStore('wallet', () => {
  // Shared state - only the essential state that needs to be centralized
  const recentTransactions = ref<RecentTransaction[]>([]);
  const preparing = ref<boolean>(false);
  const waitingForWalletConfirmation = ref<boolean>(false);
  const walletMode = ref<WalletMode>('local-bridge');

  // Initialize composables for both wallet modes
  const walletConnect = useWalletConnect();
  const injectedWallet = useInjectedWallet();
  const { disconnect: disconnectWallet, initiateConnection } = useWalletConnection();

  const { getAssetMappingHandler } = useAssetCacheStore();
  const { getChainFromChainId, updateStatePostTransaction } = useWalletHelper();
  const { prepareERC20Transfer, prepareNativeTransfer } = useTradeApi();
  const { getEvmChainName } = useSupportedChains();

  // Computed properties that delegate to the appropriate composable
  const connected = computed<boolean>(() => get(walletMode) === 'walletconnect' ? get(walletConnect.connected) : get(injectedWallet.connected));

  const connectedAddress = computed<string | undefined>(() => get(walletMode) === 'walletconnect' ? get(walletConnect.connectedAddress) : get(injectedWallet.connectedAddress));

  const connectedChainId = computed<number | undefined>(() => get(walletMode) === 'walletconnect' ? get(walletConnect.connectedChainId) : get(injectedWallet.connectedChainId));

  const supportedChainIds = computed<string[]>(() => get(walletMode) === 'walletconnect' ? get(walletConnect.supportedChainIds) : []);

  const isWalletConnect = computed<boolean>(() => get(walletMode) === 'walletconnect' ? get(walletConnect.isWalletConnect) : false);

  const supportedChainsIdForConnectedAccount = computed<number[]>(() => {
    const supportedChainIdsVal = get(supportedChainIds);
    if (supportedChainIdsVal.length === 0 || get(walletMode) === 'local-bridge') {
      // For local bridge or when no supported chains, return all supported networks
      return [1, 8453, 42161, 10, 56, 100, 137, 534352]; // mainnet, base, arbitrum, optimism, bsc, gnosis, polygon, scroll
    }
    const { getChainIdFromNamespace } = useWalletHelper();
    return supportedChainIdsVal.map(item => getChainIdFromNamespace(item));
  });

  const supportedChainsForConnectedAccount = computed<string[]>(() => get(supportedChainsIdForConnectedAccount).map(item => getChainFromChainId(item)));

  const getBrowserProvider = (): BrowserProvider => {
    if (get(walletMode) === 'local-bridge') {
      return injectedWallet.getBrowserProvider();
    }
    return walletConnect.getBrowserProvider();
  };

  const open = async (): Promise<void> => {
    if (get(walletMode) === 'local-bridge') {
      try {
        // Use the wallet connection composable for better provider detection

        await initiateConnection();
      }
      catch (error) {
        logger.error('Failed to initiate wallet connection:', error);
        // If no providers detected, throw to let the UI handle it
        throw error;
      }
    }
    else {
      await walletConnect.open();
    }
  };

  const resetState = (): void => {
    logger.debug('Resetting wallet state');
    set(preparing, false);
    set(waitingForWalletConfirmation, false);
  };

  const disconnect = async (): Promise<void> => {
    if (get(walletMode) === 'local-bridge') {
      await disconnectWallet();
    }
    else {
      await walletConnect.disconnect();
    }
    resetState();
  };

  const setWalletMode = async (mode: WalletMode | WalletMode[] | undefined): Promise<void> => {
    assert(mode !== undefined && !Array.isArray(mode), 'Mode must be a single value');
    if (get(walletMode) === mode)
      return;

    // Disconnect current mode
    await disconnect();

    // Reset state
    resetState();

    // Set new mode
    set(walletMode, mode);
  };

  const resetWalletConnection = async (): Promise<void> => {
    await disconnect();
  };

  const switchNetwork = async (chainId: bigint): Promise<void> => {
    if (get(walletMode) === 'local-bridge') {
      await injectedWallet.switchNetwork(chainId);
    }
    else {
      await walletConnect.switchNetwork(chainId);
    }
  };

  const getGasFeeForChain = async (): Promise<GasFeeEstimation> => {
    try {
      const provider = getBrowserProvider();

      const feeData = await provider.getFeeData();
      const gasPrice = feeData.gasPrice ?? feeData.maxFeePerGas ?? 0n;

      let maxAmount = '0';
      let gasFee = '0';
      const address = get(connectedAddress);
      if (address) {
        const balance = await provider.getBalance(address);
        const gasCost = gasPrice * DEFAULT_GAS_LIMIT;

        if (balance > gasCost) {
          // Add 10% buffer for gas price fluctuations
          const buffer = gasCost * 10n / 100n;
          const diff = gasCost + buffer;

          const maxSendable = balance - diff;
          gasFee = formatUnits(diff);
          maxAmount = formatUnits(maxSendable, 18);
        }
      }

      return {
        gasFee,
        maxAmount,
      };
    }
    catch (error) {
      console.error(`Error getting gas fee:`, error);
      throw error;
    }
  };

  const generateTransactionContext = async (params: TransactionParams): Promise<string> => {
    const fromAddress = get(connectedAddress) ?? 'unknown';
    const amount = params.amount;
    const id = params.assetIdentifier;
    const asset = params.native || !id
      ? id
      : await (async (): Promise<string | undefined> => {
          const mapping = await getAssetMappingHandler([id]);
          const assetMapping = mapping?.assets;
          if (!assetMapping) {
            return id;
          }
          return assetMapping[id]?.symbol ?? id;
        })();

    return `Send ${amount} ${asset ?? params.assetIdentifier} from ${fromAddress} to ${params.to}`;
  };

  const addRecentTransaction = async (hash: string, chain: string, params: TransactionParams): Promise<void> => {
    const context = await generateTransactionContext(params);
    set(recentTransactions, [
      {
        chain,
        context,
        hash,
        initiatorAddress: get(connectedAddress),
        metadata: {
          amount: bigNumberify(params.amount),
          asset: params.assetIdentifier,
        },
        status: 'pending',
        timestamp: Date.now(),
      },
      ...get(recentTransactions),
    ]);
  };

  const updateTransactionStatus = (hash: string, status: 'completed' | 'failed'): void => {
    set(
      recentTransactions,
      get(recentTransactions).map(tx =>
        tx.hash === hash
          ? { ...tx, status }
          : tx,
      ),
    );
  };

  const getRecentTransactionByTxHash = (hash: string): RecentTransaction | undefined => get(recentTransactions).find(item => item.hash === hash);

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

  const handleTransactionSuccess = async (tx: TransactionResponse, chainId: number, params: TransactionParams): Promise<void> => {
    startPromise(addRecentTransaction(tx.hash, getChainFromChainId(chainId), params));
    await tx.wait();
    updateTransactionStatus(tx.hash, 'completed');
    startPromise(updateStatePostTransaction(getRecentTransactionByTxHash(tx.hash)));
  };

  const sendTransaction = async (params: TransactionParams): Promise<TransactionResponse> => {
    // Check WalletConnect connection if in WalletConnect mode
    if (get(walletMode) === 'walletconnect') {
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
      await handleTransactionSuccess(tx, chainId, params);

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

  return {
    connected,
    connectedAddress,
    connectedChainId,
    disconnect,
    getBrowserProvider,
    getGasFeeForChain,
    isWalletConnect,
    open,
    preparing: logicOr(preparing, injectedWallet.isConnecting),
    recentTransactions,
    resetWalletConnection,
    sendTransaction,
    setWalletMode,
    supportedChainIds,
    supportedChainsForConnectedAccount,
    supportedChainsIdForConnectedAccount,
    switchNetwork,
    waitingForWalletConfirmation,
    walletMode,
  };
});
