import type { MaybeRef } from '@vueuse/core';
import { Blockchain } from '@rotki/common';
import { useTokenDetection } from '@/composables/balances/token-detection';
import { useSupportedChains } from '@/composables/info/chains';
import { useExchanges } from '@/modules/balances/exchanges/use-exchanges';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { useBlockchainTokensStore } from '@/store/blockchain/tokens';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { BlockchainRefreshButtonBehaviour } from '@/types/settings/frontend-settings';
import { arrayify } from '@/utils/array';

export const useRefresh = createSharedComposable(() => {
  const { fetchBlockchainBalances, fetchLoopringBalances } = useBlockchainBalances();
  const { fetchConnectedExchangeBalances, fetchSelectedExchangeBalances } = useExchanges();
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

    // Call all detections - they're queued internally anyway
    const detectionPromises = chains.map(async chain =>
      useTokenDetection(chain).detectTokensOfAllAddresses(),
    );
    await Promise.allSettled(detectionPromises);

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

  const refreshExchangeBalance = async (exchangeLocation: string): Promise<void> => {
    await fetchSelectedExchangeBalances(exchangeLocation);
  };

  return {
    handleBlockchainRefresh,
    massDetectTokens,
    refreshBalance,
    refreshBlockchainBalances,
    refreshExchangeBalance,
  };
});
