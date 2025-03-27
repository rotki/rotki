import type { GasFeeEstimation, RecentTransaction, TransactionError, TransactionParams } from '@/types/trade';
import { type PrepareERC20TransferResponse, type PrepareNativeTransferResponse, useTradeApi } from '@/composables/api/trade';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useSupportedChains } from '@/composables/info/chains';
import { useWalletHelper } from '@/composables/trade/wallet-helper';
import { WagmiAdapter } from '@reown/appkit-adapter-wagmi';
import { type AppKitNetwork, arbitrum, base, bsc, gnosis, mainnet, optimism, polygon, scroll } from '@reown/appkit/networks';
import { type AppKit, createAppKit, useAppKitProvider } from '@reown/appkit/vue';
import { assert, bigNumberify } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { objectOmit } from '@vueuse/shared';
import { BrowserProvider, formatUnits, type TransactionResponse } from 'ethers';

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

function buildAppKit(): AppKit {
  const projectId = import.meta.env.VITE_WALLET_CONNECT_PROJECT_ID as string;

  const wagmiAdapter = new WagmiAdapter({
    networks: supportedNetworks,
    projectId,
    ssr: false,
  });

  return createAppKit({
    adapters: [wagmiAdapter],
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

  let appKit: AppKit | undefined;

  const { assetSymbol } = useAssetInfoRetrieval();
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
    assert(appKit);

    // @ts-expect-error accessing protected method to get approved chain IDs
    const data = appKit.getApprovedCaipNetworksData();
    if (data) {
      const approvedCaipNetworkIds = data.approvedCaipNetworkIds;
      set(supportedChainIds, approvedCaipNetworkIds);
    }
  };

  const setupAppKitListener = (): void => {
    assert(appKit);

    appKit.subscribeAccount((account) => {
      set(connected, account.isConnected);
      set(connectedAddress, account.isConnected ? account.address : undefined);

      const chainId = appKit!.getCaipNetworkId();
      if (account.isConnected && chainId) {
        set(connectedChainId, chainId);
      }
      updateApprovedChainIds();
    });

    appKit.subscribeNetwork((newState) => {
      set(connectedChainId, newState.chainId);
    });
  };

  appKit = buildAppKit();
  setupAppKitListener();

  const open = async (): Promise<void> => {
    assert(appKit);
    await appKit.open();
  };

  const resetState = (): void => {
    set(connected, false);
    set(preparing, false);
    set(connectedAddress, undefined);
    set(supportedChainIds, []);
  };

  const disconnect = async (): Promise<void> => {
    assert(appKit);
    await appKit.disconnect();

    resetState();
  };

  const switchNetwork = async (chainId: bigint): Promise<void> => {
    assert(appKit);

    const network = supportedNetworks.find(item => BigInt(item.id) === chainId);
    if (network) {
      await appKit.switchNetwork(network);
    }
  };

  const getBrowserProvider = (): BrowserProvider => {
    const { walletProvider } = useAppKitProvider(EIP155);
    return new BrowserProvider(walletProvider as any);
  };

  const getGasFeeForChain = async (): Promise<GasFeeEstimation> => {
    try {
      const provider = getBrowserProvider();

      const DEFAULT_GAS_LIMIT = 21000n; // for native transfers
      const feeData = await provider.getFeeData();
      const gasPrice = feeData.gasPrice ?? feeData.maxFeePerGas ?? 0n;

      let maxAmount = '0';
      const address = get(connectedAddress);
      if (address) {
        const balance = await provider.getBalance(address);
        const gasCost = gasPrice * DEFAULT_GAS_LIMIT;

        if (balance > gasCost) {
          // Add 10% buffer for gas price fluctuations
          const buffer = gasCost * 10n / 100n;
          const maxSendable = balance - gasCost - buffer;
          maxAmount = formatUnits(maxSendable, 18);
        }
      }

      return {
        formatted: formatUnits(gasPrice, 'gwei'),
        gasPrice,
        maxAmount,
      };
    }
    catch (error) {
      console.error(`Error getting gas fee:`, error);
      throw error;
    }
  };

  const generateTransactionContext = (params: TransactionParams): string => {
    const fromAddress = get(connectedAddress) ?? 'unknown';
    const amount = params.amount;
    const asset = params.native
      ? params.assetIdentifier
      : get(assetSymbol(params.assetIdentifier));

    return `Send ${amount} ${asset} from ${fromAddress} to ${params.to}`;
  };

  const addRecentTransaction = (hash: string, chain: string, params: TransactionParams): void => {
    const context = generateTransactionContext(params);
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

  const sendTransaction = async (params: TransactionParams): Promise<TransactionResponse> => {
    assert(appKit);

    try {
      const fromAddress = get(connectedAddress);
      const provider = getBrowserProvider();
      const signer = await provider.getSigner();
      const chainId = get(connectedChainId);
      const evmChain = getEvmChainName(params.chain);

      if (!chainId || !evmChain) {
        throw new Error('No chain ID available');
      }

      assert(fromAddress);

      let tx;
      let backendPayload: PrepareERC20TransferResponse | PrepareNativeTransferResponse | undefined;
      set(preparing, true);

      if (!params.native) {
        // ERC20 transfer
        const token = params.assetIdentifier;
        assert(token);

        const payload = {
          amount: params.amount,
          fromAddress,
          toAddress: params.to,
          token,
        };
        backendPayload = await prepareERC20Transfer(payload);
      }
      else {
        // Native token transfer
        const payload = {
          amount: params.amount,
          chainId: evmChain,
          fromAddress,
          toAddress: params.to,
        };
        backendPayload = await prepareNativeTransfer(payload);
      }

      set(preparing, false);

      if (backendPayload) {
        tx = await signer.sendTransaction(objectOmit(backendPayload, ['maxPriorityFeePerGas', 'maxFeePerGas']));
        addRecentTransaction(tx.hash, getChainFromChainId(chainId), params);
        await tx.wait();
        updateTransactionStatus(tx.hash, 'completed');
        startPromise(updateStatePostTransaction(getRecentTransactionByTxHash(tx.hash)));
      }
      else {
        set(preparing, false);
        throw new Error('Failed to load the payload from backend');
      }

      return tx;
    }
    catch (error) {
      set(preparing, false);
      const txError = error as TransactionError;
      // If we have a transaction hash, update its status to failed
      if (txError.transaction?.hash) {
        updateTransactionStatus(txError.transaction.hash, 'failed');
      }
      console.error('Transaction failed:', error);
      throw error;
    }
  };

  return {
    appKit,
    connected,
    connectedAddress,
    connectedChainId,
    disconnect,
    getBrowserProvider,
    getGasFeeForChain,
    open,
    preparing,
    recentTransactions,
    sendTransaction,
    supportedChainIds,
    supportedChainsForConnectedAccount,
    supportedChainsIdForConnectedAccount,
    switchNetwork,
  };
});
