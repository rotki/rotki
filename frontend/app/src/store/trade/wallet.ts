import type { GasFeeEstimation, RecentTransaction, TransactionError, TransactionParams } from '@/types/trade';
import { useTradeApi } from '@/composables/api/trade';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useWalletHelper } from '@/composables/trade/wallet-helper';
import { WagmiAdapter } from '@reown/appkit-adapter-wagmi';
import { type AppKitNetwork, arbitrum, base, bsc, gnosis, mainnet, optimism, polygon, scroll } from '@reown/appkit/networks';
import { type AppKit, createAppKit, useAppKitProvider } from '@reown/appkit/vue';
import { assert, bigNumberify } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { BrowserProvider, formatUnits } from 'ethers';

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

  const supportedChainsIdForConnectedAccount = computed<number[]>(() => {
    const supportedChainIdsVal = get(supportedChainIds);
    if (supportedChainIdsVal.length === 0) {
      return supportedNetworks.map(item => Number(item.id));
    }
    return supportedChainIdsVal.map(item => getChainIdFromNamespace(item));
  });

  const supportedChainsForConnectedAccount = computed<string[]>(() => get(supportedChainsIdForConnectedAccount).map(item => getChainFromChainId(item)));

  const setupAppKitListener = (): void => {
    const kit = appKit;
    assert(kit);

    kit.subscribeAccount((account) => {
      set(connected, account.isConnected);
      set(connectedAddress, account.isConnected ? account.address : undefined);
      set(supportedChainIds, kit.getApprovedCaipNetworkIds());

      const chainId = kit.getCaipNetworkId();
      if (account.isConnected && chainId) {
        set(connectedChainId, chainId);
      }
    });
  };

  appKit = buildAppKit();
  setupAppKitListener();

  const open = async (): Promise<void> => {
    const kit = appKit;
    assert(kit);
    await kit.open();
  };

  const resetState = (): void => {
    set(connected, false);
    set(connectedAddress, undefined);
    set(supportedChainIds, []);
  };

  const disconnect = async (): Promise<void> => {
    const kit = appKit;
    assert(kit);
    await kit.disconnect();
    resetState();
  };

  const switchNetwork = async (chainId: bigint): Promise<void> => {
    const kit = appKit;
    assert(kit);

    const network = supportedNetworks.find(item => BigInt(item.id) === chainId);
    if (network) {
      await kit.switchNetwork(network);
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

  const sendTransaction = async (params: TransactionParams): Promise<any> => {
    try {
      const fromAddress = get(connectedAddress);
      const provider = getBrowserProvider();
      const signer = await provider.getSigner();
      const chainId = get(connectedChainId);

      if (!chainId) {
        throw new Error('No chain ID available');
      }

      assert(fromAddress);

      let tx;
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

        set(preparing, true);
        const result = await prepareERC20Transfer(payload);
        tx = await signer.sendTransaction(result);
        set(preparing, false);
      }
      else {
        // Native token transfer
        const payload = {
          amount: params.amount,
          blockchain: params.chain,
          fromAddress,
          toAddress: params.to,
        };

        set(preparing, true);
        const result = await prepareNativeTransfer(payload);
        tx = await signer.sendTransaction(result);
        set(preparing, false);
      }

      addRecentTransaction(tx.hash, getChainFromChainId(chainId), params);
      await tx.wait();
      updateTransactionStatus(tx.hash, 'completed');
      startPromise(updateStatePostTransaction(getRecentTransactionByTxHash(tx.hash)));

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
