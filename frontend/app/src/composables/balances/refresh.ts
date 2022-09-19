import { Blockchain } from '@rotki/common/lib/blockchain';
import { MaybeRef } from '@vueuse/core';
import { useExchangeBalancesStore } from '@/store/balances/exchanges';
import { useBlockchainBalancesStore } from '@/store/blockchain/balances';
import { useEthBalancesStore } from '@/store/blockchain/balances/eth';

export const useRefresh = (blockchain?: MaybeRef<Blockchain>) => {
  const { fetchBlockchainBalances } = useBlockchainBalancesStore();
  const { fetchLoopringBalances } = useEthBalancesStore();
  const { fetchConnectedExchangeBalances } = useExchangeBalancesStore();

  const refreshBlockchainBalances = async (): Promise<void> => {
    const chain = get(blockchain);
    const pending: Promise<any>[] = [
      fetchBlockchainBalances({
        ignoreCache: true,
        blockchain: chain
      })
    ];
    if (chain === Blockchain.ETH) {
      pending.push(fetchLoopringBalances(true));
    }

    await Promise.allSettled(pending);
  };

  const refreshBalance = async (balanceSource: string) => {
    if (balanceSource === 'blockchain') {
      await refreshBlockchainBalances();
    } else if (balanceSource === 'exchange') {
      await fetchConnectedExchangeBalances(true);
    }
  };

  return {
    refreshBlockchainBalances,
    refreshBalance
  };
};
