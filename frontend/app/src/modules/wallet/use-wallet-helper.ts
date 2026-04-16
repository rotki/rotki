import type { Blockchain } from '@rotki/common';
import type { RecentTransaction } from '@/modules/wallet/types';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useHistoryTransactions } from '@/modules/history/events/tx/use-history-transactions';
import { EIP155 } from './constants';

interface UseWalletHelperReturn {
  getEvmChainNameFromChainId: (chainId: number | bigint) => string;
  getChainFromChainId: (chainId: number | bigint) => Blockchain;
  getChainIdFromChain: (chain: string) => number;
  getChainIdFromNamespace: (namespace: string) => number;
  updateStatePostTransaction: (tx?: RecentTransaction) => Promise<void>;
  getEip155ChainId: (chainId: string | number) => string;
}

export function useWalletHelper(): UseWalletHelperReturn {
  const { allEvmChains, getChain } = useSupportedChains();
  const { refreshBlockchainBalances } = useBlockchainBalances();
  const { addTransactionHash } = useHistoryTransactions();

  function getEvmChainNameFromChainId(chainId: number | bigint): string {
    const id = typeof chainId === 'bigint' ? Number(chainId) : chainId;
    return get(allEvmChains).find(item => item.id === id)?.name || 'ethereum';
  }

  function getChainFromChainId(chainId: number | bigint): Blockchain {
    const name = getEvmChainNameFromChainId(chainId);
    return getChain(name);
  }

  const getChainIdFromChain = (chain: string): number => get(allEvmChains).find(item => item.name === chain)?.id || 1;

  const getEip155ChainId = (chainId: string | number): string => `${EIP155}:${chainId}`;

  const getChainIdFromNamespace = (namespace: string): number => Number(namespace.replace(`${EIP155}:`, ''));

  const updateStatePostTransaction = async (tx?: RecentTransaction): Promise<void> => {
    if (!tx)
      return;

    const { chain, initiatorAddress: address } = tx;

    await Promise.all([
      refreshBlockchainBalances({
        blockchain: chain,
      }),
      addTransactionHash({
        associatedAddress: address,
        blockchain: chain,
        txRef: tx.hash,
      }),
    ]);
  };

  return {
    getChainFromChainId,
    getChainIdFromChain,
    getChainIdFromNamespace,
    getEip155ChainId,
    getEvmChainNameFromChainId,
    updateStatePostTransaction,
  };
}
