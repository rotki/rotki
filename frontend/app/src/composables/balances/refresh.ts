import { Blockchain } from '@rotki/common/lib/blockchain';
import { BlockchainRefreshButtonBehaviour } from '@/types/settings/frontend-settings';
import type { MaybeRef } from '@vueuse/core';

export const useRefresh = createSharedComposable(() => {
  const { fetchBlockchainBalances, fetchLoopringBalances } = useBlockchainBalances();
  const { fetchConnectedExchangeBalances } = useExchangeBalancesStore();
  const { blockchainRefreshButtonBehaviour } = storeToRefs(useFrontendSettingsStore());
  const { massDetecting } = storeToRefs(useBlockchainTokensStore());
  const { txEvmChains } = useSupportedChains();

  const refreshBlockchainBalances = async (blockchain?: string): Promise<void> => {
    const chain = get(blockchain);
    const pending: Promise<any>[] = [
      fetchBlockchainBalances({
        ignoreCache: true,
        blockchain: chain,
      }),
    ];

    if (!chain || chain === Blockchain.ETH)
      pending.push(fetchLoopringBalances(true));

    await Promise.allSettled(pending);
  };

  const handleBlockchainRefresh = async (blockchain?: MaybeRef<string>, forceRedetect = false) => {
    const chain = get(blockchain);
    const behaviour = get(blockchainRefreshButtonBehaviour);

    if (behaviour === BlockchainRefreshButtonBehaviour.REDETECT_TOKENS || forceRedetect) {
      const chains = chain ? [chain] : get(txEvmChains).map(chain => chain.id);

      set(massDetecting, chain || 'all');
      await awaitParallelExecution(
        chains,
        chain => chain,
        chain => useTokenDetection(chain).detectTokensOfAllAddresses(),
        1,
      );
      set(massDetecting, undefined);
    }
    else {
      await refreshBlockchainBalances(chain);
    }
  };

  const refreshBalance = async (balanceSource: string) => {
    if (balanceSource === 'blockchain')
      await handleBlockchainRefresh();
    else if (balanceSource === 'exchange')
      await fetchConnectedExchangeBalances(true);
  };

  return {
    refreshBlockchainBalances,
    handleBlockchainRefresh,
    refreshBalance,
  };
});
