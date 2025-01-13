import { Blockchain } from '@rotki/common';
import { BlockchainRefreshButtonBehaviour } from '@/types/settings/frontend-settings';
import { awaitParallelExecution } from '@/utils/await-parallel-execution';
import { arrayify } from '@/utils/array';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useBlockchainTokensStore } from '@/store/blockchain/tokens';
import { useExchangeBalancesStore } from '@/store/balances/exchanges';
import { useBlockchainBalances } from '@/composables/blockchain/balances';
import { useTokenDetection } from '@/composables/balances/token-detection';
import { useSupportedChains } from '@/composables/info/chains';
import type { MaybeRef } from '@vueuse/core';

export const useRefresh = createSharedComposable(() => {
  const { fetchBlockchainBalances, fetchLoopringBalances } = useBlockchainBalances();
  const { fetchConnectedExchangeBalances } = useExchangeBalancesStore();
  const { blockchainRefreshButtonBehaviour } = storeToRefs(useFrontendSettingsStore());
  const { massDetecting } = storeToRefs(useBlockchainTokensStore());
  const { txEvmChains } = useSupportedChains();

  const refreshBlockchainBalances = async (blockchain?: string | string[]): Promise<void> => {
    const chain = blockchain ? arrayify(blockchain) : undefined;
    const pending: Promise<any>[] = [
      fetchBlockchainBalances({
        blockchain: chain,
        ignoreCache: true,
      }),
    ];

    if (!chain || chain.includes(Blockchain.ETH))
      pending.push(fetchLoopringBalances(true));

    await Promise.allSettled(pending);
  };

  const massDetectTokens = async (chain?: string | string[]): Promise<void> => {
    const chains = chain ? arrayify(chain) : get(txEvmChains).map(chain => chain.id);

    set(massDetecting, chain || 'all');
    await awaitParallelExecution(
      chains,
      chain => chain,
      async chain => useTokenDetection(chain).detectTokensOfAllAddresses(),
      1,
    );
    set(massDetecting, undefined);
  };

  const handleBlockchainRefresh = async (blockchain?: MaybeRef<string>, forceRedetect = false): Promise<void> => {
    const chain = get(blockchain);
    const behaviour = get(blockchainRefreshButtonBehaviour);

    if (behaviour === BlockchainRefreshButtonBehaviour.REDETECT_TOKENS || forceRedetect)
      await massDetectTokens(chain);

    else
      await refreshBlockchainBalances(chain);
  };

  const refreshBalance = async (balanceSource: string): Promise<void> => {
    if (balanceSource === 'blockchain')
      await handleBlockchainRefresh();
    else if (balanceSource === 'exchange')
      await fetchConnectedExchangeBalances(true);
  };

  return {
    handleBlockchainRefresh,
    massDetectTokens,
    refreshBalance,
    refreshBlockchainBalances,
  };
});
