import type { BlockchainBalancePayload } from '@/modules/balances/types/blockchain-balances';
import { useValueThreshold } from '@/modules/assets/amount-display/use-usd-value-threshold';
import { useBalanceQueue } from '@/modules/balances/use-balance-queue';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { arrayify } from '@/modules/core/common/data/array';
import { Section } from '@/modules/core/common/status';
import { useStatusStore } from '@/modules/core/common/use-status-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { BalanceSource } from '@/modules/settings/types/frontend-settings';
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
  const refreshState = useBalanceRefreshState();

  const isChainBusy = (chain: string): boolean =>
    getIsLoading(Section.BLOCKCHAIN, chain) || get(refreshState.refreshingChains).has(chain);

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
      if (isChainBusy(chain)) {
        if (periodic)
          return;
        await until(() => isChainBusy(chain)).toBe(false);
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
