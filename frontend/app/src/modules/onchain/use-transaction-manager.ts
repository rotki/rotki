import type { TransactionResponse } from 'ethers';
import type { Ref } from 'vue';
import type { RecentTransaction, TransactionParams } from '@/modules/onchain/types';
import { bigNumberify } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useWalletHelper } from '@/modules/onchain/use-wallet-helper';
import { useAssetCacheStore } from '@/store/assets/asset-cache';

/**
 * Composable for managing transaction state and history
 */
export function useTransactionManager(): {
  addRecentTransaction: (hash: string, chain: string, params: TransactionParams, initiatorAddress: string | undefined) => Promise<void>;
  getRecentTransactionByTxHash: (hash: string) => RecentTransaction | undefined;
  handleTransactionSuccess: (tx: TransactionResponse, chainId: number, params: TransactionParams, initiatorAddress: string | undefined, getChainFromChainId: (chainId: number) => string) => Promise<void>;
  recentTransactions: Readonly<Ref<RecentTransaction[]>>;
  updateTransactionStatus: (hash: string, status: 'completed' | 'failed') => void;
} {
  const recentTransactions = ref<RecentTransaction[]>([]);
  const { getAssetMappingHandler } = useAssetCacheStore();
  const { updateStatePostTransaction } = useWalletHelper();

  const generateTransactionContext = async (
    params: TransactionParams,
    fromAddress: string | undefined,
  ): Promise<string> => {
    const from = fromAddress ?? 'unknown';
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

    return `Send ${amount} ${asset ?? params.assetIdentifier} from ${from} to ${params.to}`;
  };

  const addRecentTransaction = async (
    hash: string,
    chain: string,
    params: TransactionParams,
    initiatorAddress: string | undefined,
  ): Promise<void> => {
    const context = await generateTransactionContext(params, initiatorAddress);
    set(recentTransactions, [
      {
        chain,
        context,
        hash,
        initiatorAddress,
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

  const getRecentTransactionByTxHash = (hash: string): RecentTransaction | undefined =>
    get(recentTransactions).find(item => item.hash === hash);

  const handleTransactionSuccess = async (
    tx: TransactionResponse,
    chainId: number,
    params: TransactionParams,
    initiatorAddress: string | undefined,
    getChainFromChainId: (chainId: number) => string,
  ): Promise<void> => {
    startPromise(addRecentTransaction(tx.hash, getChainFromChainId(chainId), params, initiatorAddress));
    await tx.wait();
    updateTransactionStatus(tx.hash, 'completed');
    startPromise(updateStatePostTransaction(getRecentTransactionByTxHash(tx.hash)));
  };

  return {
    addRecentTransaction,
    getRecentTransactionByTxHash,
    handleTransactionSuccess,
    recentTransactions,
    updateTransactionStatus,
  };
}
