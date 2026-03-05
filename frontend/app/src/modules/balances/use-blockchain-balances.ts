import type { BlockchainBalancePayload, FetchBlockchainBalancePayload } from '@/types/blockchain/balances';
import { useBalanceQueue } from '@/composables/balances/use-balance-queue';
import { useSupportedChains } from '@/composables/info/chains';
import { waitUntilIdle } from '@/composables/status';
import { useValueThreshold } from '@/composables/usd-value-threshold';
import { useStatusStore } from '@/store/status';
import { BalanceSource } from '@/types/settings/frontend-settings';
import { Section } from '@/types/status';
import { arrayify } from '@/utils/array';
import { useBalanceProcessingService } from './services/use-balance-processing-service';
import { useLoopringBalanceService } from './services/use-loopring-balance-service';

interface UseBlockchainBalancesReturn {
  fetchBlockchainBalances: (payload?: BlockchainBalancePayload, periodic?: boolean) => Promise<void>;
  fetchLoopringBalances: (refresh: boolean) => Promise<void>;
}

export function useBlockchainBalances(): UseBlockchainBalancesReturn {
  const { supportedChains } = useSupportedChains();
  const { getIsLoading } = useStatusStore();
  const valueThreshold = useValueThreshold(BalanceSource.BLOCKCHAIN);

  // Use services
  const { handleFetch } = useBalanceProcessingService();
  const { fetchLoopringBalances } = useLoopringBalanceService();
  const { queueBalanceQueries } = useBalanceQueue();

  const fetchSingleChain = async (payload: FetchBlockchainBalancePayload, periodic: boolean): Promise<void> => {
    if (getIsLoading(Section.BLOCKCHAIN, payload.blockchain)) {
      if (periodic)
        return;
      await waitUntilIdle(Section.BLOCKCHAIN, payload.blockchain);
    }

    await handleFetch(payload, get(valueThreshold));
  };

  const fetchBlockchainBalances = async (
    payload: BlockchainBalancePayload = { ignoreCache: false },
    periodic = false,
  ): Promise<void> => {
    const { addresses, blockchain, ignoreCache = false, isXpub = false } = payload;
    const chains = blockchain ? arrayify(blockchain) : get(supportedChains).map(chain => chain.id);

    await queueBalanceQueries(chains, async blockchain => fetchSingleChain({ addresses, blockchain, ignoreCache, isXpub }, periodic));
  };

  return {
    fetchBlockchainBalances,
    fetchLoopringBalances,
  };
}
