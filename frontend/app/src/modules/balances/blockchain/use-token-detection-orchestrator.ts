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
import { useDisabledChains } from '@/modules/settings/general/disabled-chain-queries/use-disabled-chains';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { DETECT_LANE_PREFIX, familyLane } from '@/modules/task-center/core/orchestrator/spec';
import { isTerminalStatus } from '@/modules/task-center/core/status';
import { type ActivityId, ActivityKind, activityParts, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

interface UseTokenDetectionOrchestratorReturn {
  detectTokens: (chain: string | string[], addresses: string[]) => Promise<void>;
  detectAllTokens: (chains?: string | string[]) => Promise<void>;
  /**
   * Detection as a stage *inside* a chain job — see {@link useBlockchainBalances}.
   *
   * `addrs` narrows the stage to specific addresses; omitted, it covers the whole chain.
   */
  detectForChain: (chain: string, parent: ActivityId, addrs?: string[]) => Promise<void>;
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
  const { isAddressExcluded } = useDisabledChains();
  const { submitTask } = useNativeTask();
  const { activities } = useTaskOrchestrator();

  /**
   * Whether detection is live for a chain, or for one address on it when `address` is given.
   *
   * @remarks
   * Callers need not filter out addresses already detecting: the deterministic activity id dedups
   * a concurrent re-submit.
   */
  function isDetectingTokens(blockchain: string, address: string | null): boolean {
    return get(activities).some((activity) => {
      if (activity.kind !== ActivityKind.TOKEN_DETECTION || isTerminalStatus(activity.status))
        return false;
      const [chain, addr] = activityParts(activity.id);
      return chain === blockchain && (address === null || addr === address);
    });
  }

  /**
   * One detection activity per address, resolving when they have all settled.
   *
   * Per-address rather than one activity for the chain, and that is deliberate: `ActivitySteps`
   * is `{ current, total }` and nothing else, so progress can say "3/9" but never *which* address;
   * and `cancel` targets an activity id, so per-account cancel needs per-account activities.
   * Folding them into the chain would delete both capabilities, not defer them.
   *
   * On the per-chain `detect:` family, never {@link BALANCES_LANE}. The chain job that awaits
   * this holds a balances slot for its whole body, so sharing that lane would deadlock it against
   * its own children.
   */
  const queueDetectionForChain = async (chain: string, addrs: string[], parent?: ActivityId): Promise<void> => {
    assert(supportsTransactions(chain));
    const detectable = addrs.filter(addr => !isAddressExcluded(chain, addr));
    if (detectable.length === 0)
      return;

    await Promise.all(detectable.map(async addr => submitTask({
      id: makeActivityId(ActivityKind.TOKEN_DETECTION, chain, addr),
      kind: ActivityKind.TOKEN_DETECTION,
      lane: familyLane(DETECT_LANE_PREFIX, chain),
      parent,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => detectTokensForAddress(runTask, chain, addr),
      subtitle: activityLabelFor(msg.$t('task_center.activity.token_detection.detect'), { address: addr, chain: getChainName(chain) }),
      title: t('task_center.group.token_detection'),
    })));
  };

  /**
   * Detection for one chain, as children of the chain job that awaits it.
   *
   * No hydration afterwards, unlike {@link detectTokens}: the chain job's own network query is
   * the next statement, and it reads the tokens this just found. Hydrating in between would be a
   * second read of the same rows.
   *
   * A chain with no addresses, or one that cannot hold tokens, is not an error — it simply has no
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

  // Detection ends in a balance read, so the chains it touched are hydrated once it settles —
  // The only coupling between the layers: work finishing triggers hydration for its subject.
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
    detectForChain,
    detectTokens,
    isDetecting: (chain: string, address: string | null = null): boolean => isDetectingTokens(chain, address),
    useIsDetecting,
  };
});
