import { Blockchain } from '@rotki/common/lib/blockchain';
import { type MaybeRef } from '@vueuse/core';
import { useTokenDetection } from '@/composables/balances/token-detection';
import { BlockchainRefreshButtonBehaviour } from '@/types/frontend-settings';

export const useRefresh = (blockchain?: MaybeRef<Blockchain>) => {
  const { fetchBlockchainBalances } = useBlockchainBalancesStore();
  const { fetchLoopringBalances } = useEthBalancesStore();
  const { fetchConnectedExchangeBalances } = useExchangeBalancesStore();

  const { blockchainRefreshButtonBehaviour } = storeToRefs(
    useFrontendSettingsStore()
  );

  const { detectTokensOfAllAddresses: detectTokensOfAllEthAddresses } =
    useTokenDetection(Blockchain.ETH);
  const { detectTokensOfAllAddresses: detectTokensOfAllOptimismAddresses } =
    useTokenDetection(Blockchain.OPTIMISM);

  const { shouldRefreshBalances } = storeToRefs(useBlockchainTokensStore());

  const refreshBlockchainBalances = async (): Promise<void> => {
    const chain = get(blockchain);
    const pending: Promise<any>[] = [
      fetchBlockchainBalances({
        ignoreCache: true,
        blockchain: chain
      })
    ];

    if (!chain || chain === Blockchain.ETH) {
      pending.push(fetchLoopringBalances(true));
    }

    await Promise.allSettled(pending);
  };

  const handleBlockchainRefresh = async () => {
    const chain = get(blockchain);
    const behaviour = get(blockchainRefreshButtonBehaviour);
    if (
      !chain &&
      behaviour === BlockchainRefreshButtonBehaviour.REDETECT_TOKENS
    ) {
      set(shouldRefreshBalances, false);
      await Promise.all([
        detectTokensOfAllEthAddresses(),
        detectTokensOfAllOptimismAddresses()
      ]);
      set(shouldRefreshBalances, true);
    }

    await refreshBlockchainBalances();
  };

  const refreshBalance = async (balanceSource: string) => {
    if (balanceSource === 'blockchain') {
      await handleBlockchainRefresh();
    } else if (balanceSource === 'exchange') {
      await fetchConnectedExchangeBalances(true);
    }
  };

  return {
    refreshBlockchainBalances,
    refreshBalance
  };
};
