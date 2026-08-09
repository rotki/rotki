import type { Result } from 'plainfp/result';
import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { TaskError } from '@/modules/core/tasks/task-result';
import { assert } from '@rotki/common';
import { isEqual } from 'es-toolkit';
import { msg } from '@/message-key';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useTokenDetectionApi } from '@/modules/balances/blockchain/use-token-detection-api';
import { useTokenDetectionStore } from '@/modules/balances/blockchain/use-token-detection-store';
import { useBalanceHydration } from '@/modules/balances/use-balance-hydration';
import { arrayify } from '@/modules/core/common/data/array';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { BALANCES_LANE } from '@/modules/task-center/core/orchestrator/spec';
import { isTerminalStatus } from '@/modules/task-center/core/status';
import { ActivityKind, activityParts, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

interface UseTokenDetectionOrchestratorReturn {
  detectTokens: (chain: string | string[], addresses: string[]) => Promise<void>;
  detectAllTokens: (chains?: string | string[]) => Promise<void>;
  /** Synchronous liveness probe — true while a matching detection activity is pending or running. */
  isDetecting: (chain: string, address?: string | null) => boolean;
  useIsDetecting: (chain: MaybeRefOrGetter<string | string[]>, address?: MaybeRefOrGetter<string | null>) => ComputedRef<boolean>;
}

export const useTokenDetectionOrchestrator = createSharedComposable((): UseTokenDetectionOrchestratorReturn => {
  const { t } = useI18n({ useScope: 'global' });
  const { detectTokensForAddress, fetchCachedDetectedTokens } = useTokenDetectionApi();
  const { setMassDetecting } = useTokenDetectionStore();
  const { addresses } = useAccountAddresses();
  const { getChainName, supportsTransactions, txEvmChains } = useSupportedChains();
  const { hydrate } = useBalanceHydration();
  const { submitTask } = useNativeTask();
  const { activities } = useTaskOrchestrator();

  // Liveness comes from the orchestrator: any non-terminal TOKEN_DETECTION activity whose id
  // parts (`chain`, `address`) match. The deterministic id also dedups concurrent re-submits, so
  // the old "skip already-detecting addresses" filter is no longer needed.
  function isDetectingTokens(blockchain: string, address: string | null): boolean {
    return get(activities).some((activity) => {
      if (activity.kind !== ActivityKind.TOKEN_DETECTION || isTerminalStatus(activity.status))
        return false;
      const [chain, addr] = activityParts(activity.id);
      return chain === blockchain && (address === null || addr === address);
    });
  }

  const queueDetectionForChain = async (chain: string, addrs: string[]): Promise<void> => {
    assert(supportsTransactions(chain));
    await Promise.all(addrs.map(async addr => submitTask({
      id: makeActivityId(ActivityKind.TOKEN_DETECTION, chain, addr),
      kind: ActivityKind.TOKEN_DETECTION,
      lane: BALANCES_LANE,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => detectTokensForAddress(runTask, chain, addr),
      subtitle: activityLabelFor(msg.$t('task_center.activity.token_detection.detect'), { address: addr, chain: getChainName(chain) }),
      title: t('task_center.group.token_detection'),
    })));
  };

  // Detection ends in a balance read, so the chains it touched are hydrated once it settles —
  // §4's only coupling between the layers: work finishing triggers hydration for its subject.
  const reloadBalancesForChains = async (chains: string[]): Promise<void> => {
    await hydrate({ blockchain: chains });
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
      await fetchCachedDetectedTokens(c);
    }
  });

  return {
    detectAllTokens,
    detectTokens,
    isDetecting: (chain: string, address: string | null = null): boolean => isDetectingTokens(chain, address),
    useIsDetecting,
  };
});
