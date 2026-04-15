import type { MaybeRef } from 'vue';
import { Blockchain } from '@rotki/common';
import { useTokenDetectionOrchestrator } from '@/modules/balances/blockchain/use-token-detection-orchestrator';
import { useExchanges } from '@/modules/balances/exchanges/use-exchanges';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { BlockchainRefreshButtonBehaviour } from '@/modules/settings/types/frontend-settings';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { arrayify } from '@/utils/array';

export const useBalanceRefresh = createSharedComposable(() => {
  const { fetchLoopringBalances, refreshBlockchainBalances } = useBlockchainBalances();
  const { fetchConnectedExchangeBalances, fetchSelectedExchangeBalances } = useExchanges();
  const { blockchainRefreshButtonBehaviour } = storeToRefs(useFrontendSettingsStore());

  const refreshBlockchainBalancesFn = async (blockchain?: string | string[]): Promise<void> => {
    const chain = blockchain ? arrayify(blockchain) : undefined;
    const pending: Promise<any>[] = [
      refreshBlockchainBalances({
        blockchain: chain,
      }),
    ];

    if (!chain || chain.includes(Blockchain.ETH))
      pending.push(fetchLoopringBalances(true));

    await Promise.allSettled(pending);
  };

  const { detectAllTokens } = useTokenDetectionOrchestrator();

  const massDetectTokens = async (chain?: string | string[]): Promise<void> => {
    await detectAllTokens(chain);
  };

  const handleBlockchainRefresh = async (blockchain?: MaybeRef<string | string[]>, forceRedetect = false): Promise<void> => {
    const chain = get(blockchain);
    const behaviour = get(blockchainRefreshButtonBehaviour);

    if (behaviour === BlockchainRefreshButtonBehaviour.REDETECT_TOKENS || forceRedetect)
      await massDetectTokens(chain);

    else
      await refreshBlockchainBalancesFn(chain);
  };

  const refreshBalance = async (balanceSource: string): Promise<void> => {
    if (balanceSource === 'blockchain')
      await handleBlockchainRefresh();
    else if (balanceSource === 'exchange')
      await fetchConnectedExchangeBalances(true);
  };

  const refreshExchangeBalance = async (exchangeLocation: string): Promise<void> => {
    await fetchSelectedExchangeBalances(exchangeLocation);
  };

  return {
    handleBlockchainRefresh,
    massDetectTokens,
    refreshBalance,
    refreshBlockchainBalances: refreshBlockchainBalancesFn,
    refreshExchangeBalance,
  };
});
