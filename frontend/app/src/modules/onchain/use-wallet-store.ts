import type UniversalProvider from '@walletconnect/universal-provider';
import type {
  GasFeeEstimation,
  PrepareERC20TransferResponse,
  PrepareNativeTransferResponse,
  RecentTransaction,
  TransactionParams,
} from '@/modules/onchain/types';
import { EthersAdapter } from '@reown/appkit-adapter-ethers';
import { type AppKitNetwork, arbitrum, base, bsc, gnosis, mainnet, optimism, polygon, scroll } from '@reown/appkit/networks';
import { type AppKit, createAppKit } from '@reown/appkit/vue';
import { bigNumberify } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { BrowserProvider, formatUnits, getAddress, type TransactionResponse } from 'ethers';
import { useInterop } from '@/composables/electron-interop';
import { useSupportedChains } from '@/composables/info/chains';
import { useWalletHelper } from '@/modules/onchain/use-wallet-helper';
import { useAssetCacheStore } from '@/store/assets/asset-cache';
import { logger } from '@/utils/logging';
import { useTradeApi } from './send/use-trade-api';
import {
  handleTransactionError,
  prepareTransactionPayload,
  validateTransactionRequirements,
} from './transaction-helpers';

export const ROTKI_DAPP_METADATA = {
  description: 'Rotki Dapp',
  icons: ['https://raw.githubusercontent.com/rotki/data/refs/heads/main/assets/default_icons/website_logo.png'],
  name: 'Rotki Dapp',
  url: 'https://rotki.com',
};

export const EIP155 = 'eip155';

export const supportedNetworks: [AppKitNetwork, ...AppKitNetwork[]] = [
  mainnet,
  base,
  arbitrum,
  optimism,
  bsc,
  gnosis,
  polygon,
  scroll,
] as const;

const DEFAULT_GAS_LIMIT = 21000n; // for native transfers

function buildAppKit(): AppKit {
  const projectId = import.meta.env.VITE_WALLET_CONNECT_PROJECT_ID as string;

  return createAppKit({
    adapters: [new EthersAdapter()],
    allowUnsupportedChain: true,
    features: {
      analytics: true,
      email: false,
      onramp: false,
      socials: false,
      swaps: false,
    },
    metadata: ROTKI_DAPP_METADATA,
    networks: supportedNetworks,
    projectId,
  });
}

export const useWalletStore = defineStore('wallet', () => {
  const connected = ref<boolean>(false);
  const connectedAddress = ref<string>();
  const connectedChainId = ref<number>();
  const supportedChainIds = ref<string[]>([]);
  const recentTransactions = ref<RecentTransaction[]>([]);
  const preparing = ref<boolean>(false);
  const waitingForWalletConfirmation = ref<boolean>(false);
  const isWalletConnect = ref<boolean>(false);

  let appKit: AppKit | undefined;

  const getAppKit = (): AppKit => {
    if (!appKit) {
      logger.debug('Initializing AppKit');
      appKit = buildAppKit();
      setupAppKitListener();
    }
    return appKit;
  };

  const { getAssetMappingHandler } = useAssetCacheStore();
  const { getChainFromChainId, getChainIdFromNamespace, updateStatePostTransaction } = useWalletHelper();
  const { prepareERC20Transfer, prepareNativeTransfer } = useTradeApi();
  const { getEvmChainName } = useSupportedChains();

  const supportedChainsIdForConnectedAccount = computed<number[]>(() => {
    const supportedChainIdsVal = get(supportedChainIds);
    if (supportedChainIdsVal.length === 0) {
      return supportedNetworks.map(item => Number(item.id));
    }
    return supportedChainIdsVal.map(item => getChainIdFromNamespace(item));
  });

  const supportedChainsForConnectedAccount = computed<string[]>(() => get(supportedChainsIdForConnectedAccount).map(item => getChainFromChainId(item)));

  const updateApprovedChainIds = (): void => {
    const appKitInstance = getAppKit();

    // @ts-expect-error accessing protected method to get approved chain IDs
    const data = appKitInstance.getApprovedCaipNetworksData();
    if (data) {
      const approvedCaipNetworkIds = data.approvedCaipNetworkIds;
      set(supportedChainIds, approvedCaipNetworkIds);
    }
  };

  const getBrowserProvider = (): BrowserProvider => {
    const appKitInstance = getAppKit();
    const walletProvider = appKitInstance.getProvider(EIP155);
    return new BrowserProvider(walletProvider as any);
  };

  function setupAppKitListener(): void {
    if (!appKit)
      return;

    appKit.subscribeAccount((account) => {
      if (!appKit)
        return;

      set(connected, account.isConnected);
      set(connectedAddress, account.isConnected && account.address ? getAddress(account.address) : undefined);

      if (account.isConnected) {
        const provider: any = appKit.getProvider(EIP155);
        set(isWalletConnect, provider && 'isWalletConnect' in provider && provider.isWalletConnect);

        const chainId = appKit.getCaipNetworkId();
        if (chainId) {
          set(connectedChainId, chainId);
        }
      }

      updateApprovedChainIds();
    });

    appKit.subscribeNetwork((newState) => {
      set(connectedChainId, newState.chainId);
    });
  }

  const open = async (): Promise<void> => {
    const appKitInstance = getAppKit();
    await appKitInstance.open();
  };

  const resetState = (): void => {
    logger.debug('Resetting wallet state');
    set(connected, false);
    set(preparing, false);
    set(connectedAddress, undefined);
    set(supportedChainIds, []);
    set(isWalletConnect, false);
    set(waitingForWalletConfirmation, false);
    appKit = undefined;
  };

  const disconnect = async (): Promise<void> => {
    if (appKit) {
      await appKit.disconnect();
    }
    resetState();
  };

  const { isPackaged } = useInterop();

  const resetWalletConnection = async (): Promise<void> => {
    if (isPackaged) {
      await disconnect();
    }
  };

  const switchNetwork = async (chainId: bigint): Promise<void> => {
    const appKitInstance = getAppKit();

    const network = supportedNetworks.find(item => BigInt(item.id) === chainId);
    if (network) {
      await appKitInstance.switchNetwork(network);
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

  const checkWalletConnection = async (universalProvider: UniversalProvider | undefined): Promise<void> => {
    if (!universalProvider?.isWalletConnect)
      return;

    try {
      const session = universalProvider.session;
      if (session?.topic) {
        set(preparing, true);
        const pingPromise = universalProvider.client.ping({ topic: session.topic });
        const timeoutPromise = new Promise((_, reject) => {
          setTimeout(() => reject(new Error('Ping timeout after 5s')), 5000);
        });

        await Promise.race([pingPromise, timeoutPromise]);
      }
    }
    catch {
      throw new Error('It seems that your wallet is inactive. If you are using browser wallet bridge, make sure the page is open.');
    }
    finally {
      set(preparing, false);
    }
  };

  const sendTransaction = async (params: TransactionParams): Promise<TransactionResponse> => {
    const appKitInstance = getAppKit();

    const universalProvider = await appKitInstance.getUniversalProvider();
    await checkWalletConnection(universalProvider);

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
    preparing,
    recentTransactions,
    resetWalletConnection,
    sendTransaction,
    supportedChainsForConnectedAccount,
    supportedChainsIdForConnectedAccount,
    switchNetwork,
    waitingForWalletConfirmation,
  };
});
