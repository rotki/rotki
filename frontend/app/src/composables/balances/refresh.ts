import { Blockchain } from '@rotki/common/lib/blockchain';
import { type MaybeRef } from '@vueuse/core';
import { BlockchainRefreshButtonBehaviour } from '@/types/settings/frontend-settings';

export const useRefresh = (blockchain?: MaybeRef<Blockchain>) => {
  const { fetchBlockchainBalances } = useBlockchainBalances();
  const { fetchLoopringBalances } = useEthBalancesStore();
  const { fetchConnectedExchangeBalances } = useExchangeBalancesStore();

  const { blockchainRefreshButtonBehaviour } = storeToRefs(
    useFrontendSettingsStore()
  );

  const { detectTokensOfAllAddresses: detectTokensOfAllEthAddresses } =
    useTokenDetection(Blockchain.ETH);
  const { detectTokensOfAllAddresses: detectTokensOfAllOptimismAddresses } =
    useTokenDetection(Blockchain.OPTIMISM);
  const { detectTokensOfAllAddresses: detectTokensOfAllPolygonAddresses } =
    useTokenDetection(Blockchain.POLYGON_POS);
  const { detectTokensOfAllAddresses: detectTokensOfAllArbitrumAddresses } =
    useTokenDetection(Blockchain.ARBITRUM_ONE);
  const { detectTokensOfAllAddresses: detectTokensOfAllBaseAddresses } =
    useTokenDetection(Blockchain.BASE);
  const { detectTokensOfAllAddresses: detectTokensOfAllGnosisAddresses } =
    useTokenDetection(Blockchain.GNOSIS);

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
    if (behaviour === BlockchainRefreshButtonBehaviour.REDETECT_TOKENS) {
      const promises = [];
      if (!chain || chain === Blockchain.ETH) {
        promises.push(detectTokensOfAllEthAddresses());
      }
      if (!chain || chain === Blockchain.OPTIMISM) {
        promises.push(detectTokensOfAllOptimismAddresses());
      }
      if (!chain || chain === Blockchain.POLYGON_POS) {
        promises.push(detectTokensOfAllPolygonAddresses());
      }
      if (!chain || chain === Blockchain.ARBITRUM_ONE) {
        promises.push(detectTokensOfAllArbitrumAddresses());
      }
      if (!chain || chain === Blockchain.BASE) {
        promises.push(detectTokensOfAllBaseAddresses());
      }
      if (!chain || chain === Blockchain.GNOSIS) {
        promises.push(detectTokensOfAllGnosisAddresses());
      }

      set(shouldRefreshBalances, false);
      await Promise.all(promises);
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
    handleBlockchainRefresh,
    refreshBalance
  };
};
