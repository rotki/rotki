import type { BlockchainBalancePayload } from '@/types/blockchain/accounts';
import { useBalanceQueue } from '@/composables/balances/use-balance-queue';
import { useSupportedChains } from '@/composables/info/chains';
import { useUsdValueThreshold } from '@/composables/usd-value-threshold';
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
  const { isLoading } = useStatusStore();
  const usdValueThreshold = useUsdValueThreshold(BalanceSource.BLOCKCHAIN);

  // Use services
  const { handleFetch } = useBalanceProcessingService();
  const { fetchLoopringBalances } = useLoopringBalanceService();

  const fetchSingleChain = async (blockchain: string, ignoreCache: boolean, periodic: boolean): Promise<void> => {
    const loading = isLoading(Section.BLOCKCHAIN, blockchain);

    // Skip if already loading and this is a periodic call
    if (get(loading) && periodic)
      return;

    // Wait for existing operation to complete if not periodic
    if (get(loading))
      await until(loading).toBe(false);

    await handleFetch(blockchain, ignoreCache, get(usdValueThreshold));
  };

  const fetchBlockchainBalances = async (
    payload: BlockchainBalancePayload = { ignoreCache: false },
    periodic = false,
  ): Promise<void> => {
    const { blockchain, ignoreCache = false } = payload;
    const chains = blockchain ? arrayify(blockchain) : get(supportedChains).map(chain => chain.id);

    const { queueBalanceQueries } = useBalanceQueue();
    await queueBalanceQueries(chains, async chain => fetchSingleChain(chain, ignoreCache, periodic));
  };

  return {
    fetchBlockchainBalances,
    fetchLoopringBalances,
  };
}
