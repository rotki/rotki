import type {
  GasFeeEstimation,
  PrepareERC20TransferResponse,
  PrepareNativeTransferResponse,
  RecentTransaction,
  TransactionParams,
} from '@/modules/onchain/types';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useInterop } from '@/composables/electron-interop';
import { useSupportedChains } from '@/composables/info/chains';
import { useWalletHelper } from '@/modules/onchain/use-wallet-helper';
import { WagmiAdapter } from '@reown/appkit-adapter-wagmi';
import { type AppKitNetwork, arbitrum, base, bsc, gnosis, mainnet, optimism, polygon, scroll } from '@reown/appkit/networks';
import { type AppKit, createAppKit, useAppKitProvider } from '@reown/appkit/vue';
import { assert, bigNumberify } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { BrowserProvider, formatUnits, type TransactionResponse } from 'ethers';
import { useTradeApi } from './send/use-trade-api';

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

function buildAppKit(isPackaged: boolean): AppKit {
  const projectId = isPackaged ? import.meta.env.VITE_WALLET_CONNECT_PROJECT_ID as string : 'a8a07e2bdf6f30c0f749ba31504766bf';

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
  const waitingForWalletConfirmation = ref<boolean>(false);
  const isWalletConnect = ref<boolean>(false);
  const { isPackaged } = useInterop();

  const appKit: AppKit = buildAppKit(isPackaged);

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

  const getBrowserProvider = (): BrowserProvider => {
    const { walletProvider } = useAppKitProvider(EIP155);
    return new BrowserProvider(walletProvider as any);
  };

  const setupAppKitListener = (): void => {
    assert(appKit);

    appKit.subscribeAccount((account) => {
      assert(appKit);

      set(connected, account.isConnected);
      set(connectedAddress, account.isConnected ? account.address : undefined);

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
  };

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
    set(isWalletConnect, false);
    set(waitingForWalletConfirmation, false);
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

  const getGasFeeForChain = async (): Promise<GasFeeEstimation> => {
    try {
      const provider = getBrowserProvider();

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

    return `Send ${amount} ${asset || params.assetIdentifier} from ${fromAddress} to ${params.to}`;
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
          chain: evmChain,
          fromAddress,
          toAddress: params.to,
        };
        backendPayload = await prepareNativeTransfer(payload);
      }

      set(preparing, false);

      if (backendPayload) {
        set(waitingForWalletConfirmation, true);
        const provider = getBrowserProvider();
        const signer = await provider.getSigner();
        tx = await signer.sendTransaction(backendPayload);
        set(waitingForWalletConfirmation, false);
        addRecentTransaction(tx.hash, getChainFromChainId(chainId), params);
        await tx.wait();
        updateTransactionStatus(tx.hash, 'completed');
        startPromise(updateStatePostTransaction(getRecentTransactionByTxHash(tx.hash)));
      }
      else {
        throw new Error('Failed to load the payload from backend');
      }

      return tx;
    }
    catch (error) {
      set(preparing, false);
      set(waitingForWalletConfirmation, false);

      // If it's a transaction error with a hash, update its status
      if (error && typeof error === 'object' && 'transaction' in error
        && error.transaction && typeof error.transaction === 'object'
        && 'hash' in error.transaction && error.transaction.hash
        && typeof error.transaction.hash === 'string') {
        updateTransactionStatus(error.transaction.hash, 'failed');
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
    isWalletConnect,
    open,
    preparing,
    recentTransactions,
    sendTransaction,
    supportedChainIds,
    supportedChainsForConnectedAccount,
    supportedChainsIdForConnectedAccount,
    switchNetwork,
    waitingForWalletConfirmation,
  };
});
