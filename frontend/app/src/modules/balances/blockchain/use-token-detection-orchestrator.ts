import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { assert } from '@rotki/common';
import { isEqual } from 'es-toolkit';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useTokenDetectionApi } from '@/modules/balances/blockchain/use-token-detection-api';
import { useTokenDetectionStore } from '@/modules/balances/blockchain/use-token-detection-store';
import { useBalanceQueue } from '@/modules/balances/use-balance-queue';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { arrayify } from '@/modules/core/common/data/array';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { TaskType } from '@/modules/core/tasks/task-type';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';

interface UseTokenDetectionOrchestratorReturn {
  detectTokens: (chain: string | string[], addresses: string[]) => Promise<void>;
  detectAllTokens: (chains?: string | string[]) => Promise<void>;
  useIsDetecting: (chain: MaybeRefOrGetter<string | string[]>, address?: MaybeRefOrGetter<string | null>) => ComputedRef<boolean>;
}

export const useTokenDetectionOrchestrator = createSharedComposable((): UseTokenDetectionOrchestratorReturn => {
  const { fetchDetectedTokens } = useTokenDetectionApi();
  const { setMassDetecting } = useTokenDetectionStore();
  const { addresses } = useAccountAddresses();
  const { supportsTransactions, txEvmChains } = useSupportedChains();
  const { fetchBlockchainBalances } = useBlockchainBalances();
  const { queueTokenDetection } = useBalanceQueue();
  const { isTaskRunning } = useTaskStore();

  function isDetectingTokens(blockchain: string, address: string | null): boolean {
    return isTaskRunning(TaskType.FETCH_DETECTED_TOKENS, {
      chain: blockchain,
      ...(address ? { address } : {}),
    });
  }

  const queueDetectionForChain = async (chain: string, addrs: string[]): Promise<void> => {
    assert(supportsTransactions(chain));
    const filteredAddresses = addrs.filter(addr => !isDetectingTokens(chain, addr));
    if (filteredAddresses.length > 0)
      await queueTokenDetection(chain, filteredAddresses, async addr => fetchDetectedTokens(chain, addr));
  };

  const reloadBalancesForChains = async (chains: string[]): Promise<void> => {
    await Promise.allSettled(chains.map(async chain =>
      fetchBlockchainBalances({
        blockchain: chain,
      }),
    ));
  };

  const detectTokens = async (
    chain: string | string[],
    addrs: string[],
  ): Promise<void> => {
    const chains = arrayify(chain);
    await Promise.all(chains.map(async c => queueDetectionForChain(c, addrs)));
    await reloadBalancesForChains(chains);
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

      await reloadBalancesForChains(chains);
    }
    finally {
      setMassDetecting(undefined);
    }
  };

  const useIsDetecting = (
    chain: MaybeRefOrGetter<string | string[]>,
    address: MaybeRefOrGetter<string | null> = null,
  ): ComputedRef<boolean> => computed<boolean>(() => {
    const addr = toValue(address);
    return arrayify(toValue(chain)).some(blockchain => isDetectingTokens(blockchain, addr));
  });

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

      // Fetch cached detections only — no balance refresh
      await fetchDetectedTokens(c);
    }
  });

  return {
    detectAllTokens,
    detectTokens,
    useIsDetecting,
  };
});
