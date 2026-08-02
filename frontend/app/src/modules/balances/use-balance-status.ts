import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

interface UseBalanceStatusReturn {
  hasCachedData: ComputedRef<boolean>;
  isInitialLoading: ComputedRef<boolean>;
  isRefreshing: ComputedRef<boolean>;
}

/**
 * Per-chain or aggregate view of blockchain balance loading, answered by the orchestrator's
 * completion ledger rather than a hand-maintained status map.
 *
 * A chain runs under two activity ids (`…:<chain>` for the network refresh, `…:<chain>:cached` for
 * the DB read), so a per-chain read is a prefix aggregate over both. Chains that hold no accounts
 * never submit an activity at all: `markCompleted` is what puts those in the ledger.
 *
 * Aggregate semantics (no chain arg):
 * - hasCachedData: at least one chain has ever completed
 * - isInitialLoading: nothing has ever completed and something is in flight, i.e. there is
 *   genuinely nothing to show yet. Once the first chain lands the rest fill in behind it.
 * - isRefreshing: at least one chain has an in-flight refresh POST
 */
export function useBalanceStatus(chain?: MaybeRefOrGetter<string>): UseBalanceStatusReturn {
  const { useWorkStatus, useWorkStatusPrefix } = useTaskOrchestrator();
  const refreshState = useBalanceRefreshState();

  const status = chain === undefined
    ? useWorkStatus(ActivityKind.BLOCKCHAIN_BALANCES)
    : useWorkStatusPrefix(ActivityKind.BLOCKCHAIN_BALANCES, () => toValue(chain));

  const hasCachedData = computed<boolean>(() => get(status).everCompleted);

  const isInitialLoading = computed<boolean>(() => {
    const { active, everCompleted } = get(status);
    return active && !everCompleted;
  });

  const { isRefreshing: anyIsRefreshing } = storeToRefs(refreshState);
  const isRefreshing = chain === undefined
    ? anyIsRefreshing
    : refreshState.useIsRefreshing(chain);

  return {
    hasCachedData,
    isInitialLoading,
    isRefreshing,
  };
}
