import type { BlockchainBalancePayload } from '@/types/blockchain/balances';
import { useSupportedChains } from '@/composables/info/chains';
import { waitUntilIdle } from '@/composables/status';
import { useValueThreshold } from '@/composables/usd-value-threshold';
import { useBalanceQueue } from '@/modules/balances/use-balance-queue';
import { useStatusStore } from '@/store/status';
import { BalanceSource } from '@/types/settings/frontend-settings';
import { Section } from '@/types/status';
import { arrayify } from '@/utils/array';
import { useBalanceProcessingService } from './services/use-balance-processing-service';
import { useLoopringBalanceService } from './services/use-loopring-balance-service';

interface UseBlockchainBalancesReturn {
  fetchBlockchainBalances: (payload?: BlockchainBalancePayload) => Promise<void>;
  refreshBlockchainBalances: (payload?: BlockchainBalancePayload, periodic?: boolean) => Promise<void>;
  fetchLoopringBalances: (refresh: boolean) => Promise<void>;
}

export function useBlockchainBalances(): UseBlockchainBalancesReturn {
  const { supportedChains } = useSupportedChains();
  const { getIsLoading } = useStatusStore();
  const valueThreshold = useValueThreshold(BalanceSource.BLOCKCHAIN);

  const { handleCachedFetch, handleRefresh } = useBalanceProcessingService();
  const { fetchLoopringBalances } = useLoopringBalanceService();
  const { queueBalanceQueries } = useBalanceQueue();

  // Cached DB read — always fires immediately, no loading checks needed
  const fetchBlockchainBalances = async (
    payload: BlockchainBalancePayload = {},
  ): Promise<void> => {
    const { addresses, blockchain, isXpub = false } = payload;
    const chains = blockchain ? arrayify(blockchain) : get(supportedChains).map(chain => chain.id);
    await Promise.allSettled(
      chains.map(async (chain) => {
        await handleCachedFetch({ addresses, blockchain: chain, isXpub }, get(valueThreshold));
      }),
    );
  };

  // Network refresh — queued with loading checks to avoid overloading nodes
  const refreshBlockchainBalances = async (
    payload: BlockchainBalancePayload = {},
    periodic = false,
  ): Promise<void> => {
    const { addresses, blockchain, isXpub = false } = payload;
    const chains = blockchain ? arrayify(blockchain) : get(supportedChains).map(chain => chain.id);
    await queueBalanceQueries(chains, async (chain) => {
      if (getIsLoading(Section.BLOCKCHAIN, chain)) {
        if (periodic)
          return;
        await waitUntilIdle(Section.BLOCKCHAIN, chain);
      }
      await handleRefresh({ addresses, blockchain: chain, isXpub });
    });
  };

  return {
    fetchBlockchainBalances,
    fetchLoopringBalances,
    refreshBlockchainBalances,
  };
}
