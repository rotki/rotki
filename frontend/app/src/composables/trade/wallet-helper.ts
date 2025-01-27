import type { RecentTransaction } from '@/types/trade';
import { useHistoryTransactions } from '@/composables/history/events/tx';
import { useSupportedChains } from '@/composables/info/chains';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { EIP155 } from '@/store/trade/wallet';
import { assert, type Blockchain } from '@rotki/common';

interface UseWalletHelperReturn {
  getChainFromChainId: (chainId: number) => Blockchain;
  getChainIdFromChain: (chain: string) => number;
  getChainIdFromNamespace: (namespace: string) => number;
  updateStatePostTransaction: (tx?: RecentTransaction) => Promise<void>;
}

export function useWalletHelper(): UseWalletHelperReturn {
  const { allEvmChains, getChain, getEvmChainName } = useSupportedChains();
  const { fetchBlockchainBalances } = useBlockchainBalances();
  const { addTransactionHash } = useHistoryTransactions();

  function getChainFromChainId(chainId: number): Blockchain {
    const name = get(allEvmChains).find(item => item.id === chainId)?.name || 'ethereum';
    return getChain(name);
  }

  const getChainIdFromChain = (chain: string): number => get(allEvmChains).find(item => item.name === chain)?.id || 1;

  const getChainIdFromNamespace = (namespace: string): number => Number(namespace.replace(`${EIP155}:`, ''));

  const updateStatePostTransaction = async (tx?: RecentTransaction): Promise<void> => {
    if (!tx)
      return;

    const { chain, initiatorAddress: address } = tx;
    const evmChain = getEvmChainName(chain);
    assert(evmChain);

    await Promise.all([
      fetchBlockchainBalances({
        blockchain: chain,
        ignoreCache: true,
      }),
      addTransactionHash({
        associatedAddress: address,
        evmChain,
        txHash: tx.hash,
      }),
    ]);
  };

  return {
    getChainFromChainId,
    getChainIdFromChain,
    getChainIdFromNamespace,
    updateStatePostTransaction,
  };
}
