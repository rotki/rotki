import type { ActivityId } from '@/modules/task-center/core/types';
import { createSharedComposable } from '@vueuse/core';
import { get } from '@vueuse/shared';
import { isEqual } from 'es-toolkit';
import { computed, type ComputedRef, type MaybeRefOrGetter, watch } from 'vue';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useTokenDetectionActivity } from '@/modules/balances/blockchain/use-token-detection-activity';
import { useTokenDetectionApi } from '@/modules/balances/blockchain/use-token-detection-api';
import { useTokenDetectionStore } from '@/modules/balances/blockchain/use-token-detection-store';
import { useTokenDetectionTasks } from '@/modules/balances/blockchain/use-token-detection-tasks';
import { useBalanceHydration } from '@/modules/balances/use-balance-hydration';
import { arrayify } from '@/modules/core/common/data/array';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

interface UseTokenDetectionOrchestratorReturn {
  detectTokens: (chain: string | string[], addresses: string[]) => Promise<void>;
  detectAllTokens: (chains?: string | string[]) => Promise<void>;
  /**
   * Detection as a stage *inside* a chain job (see {@link useBlockchainBalances}).
   *
   * `addrs` narrows the stage to specific addresses; omitted, it covers the whole chain.
   */
  detectForChain: (chain: string, parent: ActivityId, addrs?: string[]) => Promise<void>;
  /** Synchronous liveness probe: true while a matching detection activity is pending or running. */
  isDetecting: (chain: string, address?: string | null) => boolean;
  useIsDetecting: (chain: MaybeRefOrGetter<string | string[]>, address?: MaybeRefOrGetter<string | null>) => ComputedRef<boolean>;
}

export const useTokenDetectionOrchestrator = createSharedComposable((): UseTokenDetectionOrchestratorReturn => {
  const { fetchCachedDetectedTokens } = useTokenDetectionApi();
  const { setMassDetecting } = useTokenDetectionStore();
  const { addresses } = useAccountAddresses();
  const { supportsTransactions, txEvmChains } = useSupportedChains();
  const { hydrate } = useBalanceHydration();
  const { isDetectingTokens, useIsDetecting } = useTokenDetectionActivity();
  const { queueDetectionForChain } = useTokenDetectionTasks();

  /**
   * Detection for one chain, as children of the chain job that awaits it.
   *
   * No hydration afterwards, unlike {@link detectTokens}: the chain job's own network query is
   * the next statement, and it reads the tokens this just found. Hydrating in between would be a
   * second read of the same rows.
   *
   * A chain with no addresses, or one that cannot hold tokens, is not an error. It simply has no
   * detection stage, and the chain job carries straight on to its query.
   *
   * `addrs` narrows the stage. An account addition knows exactly which addresses are new, and
   * detecting the chain's other fifty would be work nobody asked for; every other caller wants the
   * whole chain and passes nothing.
   */
  const detectForChain = async (chain: string, parent: ActivityId, addrs?: string[]): Promise<void> => {
    if (!supportsTransactions(chain))
      return;

    const chainAddresses = addrs ?? get(addresses)[chain] ?? [];
    if (chainAddresses.length === 0)
      return;

    await queueDetectionForChain(chain, chainAddresses, parent);
  };

  /**
   * Detects tokens for the given addresses and hydrates the balances of every chain it touched.
   *
   * @remarks
   * Hydration is part of the contract: awaiting this call is what makes the newly detected token
   * balances readable from the store.
   */
  const detectTokens = async (
    chain: string | string[],
    addrs: string[],
  ): Promise<void> => {
    const chains = arrayify(chain);
    await Promise.all(chains.map(async c => queueDetectionForChain(c, addrs)));
    await hydrate({ blockchain: chains });
  };

  const detectAllTokens = async (
    chain?: string | string[],
  ): Promise<void> => {
    const chains = chain ? arrayify(chain) : get(txEvmChains).map(c => c.id);

    setMassDetecting(chains.join(',') || 'all');

    try {
      const addressesValue = get(addresses);
      await Promise.allSettled(chains.map(async (c) => {
        if (!supportsTransactions(c))
          return;

        const tokenAddresses = addressesValue[c] ?? [];
        if (tokenAddresses.length > 0)
          await queueDetectionForChain(c, tokenAddresses);
      }));

      await hydrate({ blockchain: chains });
    }
    finally {
      setMassDetecting(undefined);
    }
  };

  // Watcher: sync cached detection data when monitored addresses change
  const monitoredAddresses = computed<Record<string, string[]>>(() => {
    const addressesPerChain = get(addresses);
    return Object.fromEntries(get(txEvmChains).map(c => [c.id, addressesPerChain[c.id] ?? []]));
  });

  watch(monitoredAddresses, async (curr, prev) => {
    for (const c in curr) {
      const addrs = curr[c];
      if (!addrs || addrs.length === 0 || isEqual(addrs, prev[c]))
        continue;

      // Fetch cached detections only, no balance refresh
      await fetchCachedDetectedTokens(c);
    }
  });

  return {
    detectAllTokens,
    detectForChain,
    detectTokens,
    isDetecting: (chain: string, address: string | null = null): boolean => isDetectingTokens(chain, address),
    useIsDetecting,
  };
});
