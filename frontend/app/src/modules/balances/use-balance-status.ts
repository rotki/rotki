import { get } from '@vueuse/shared';
import { isEqual } from 'es-toolkit';
import { storeToRefs } from 'pinia';
import { computed, type ComputedRef, type MaybeRefOrGetter, toValue } from 'vue';
import { chainBalancesActivity } from '@/modules/balances/balances.activity';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { ActivityStatus, type WorkStatus } from '@/modules/task-center/core/types';
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
 * A chain's *work* runs under one activity id (`…:<chain>`), so a per-chain read is a prefix
 * aggregate. Chains that hold no accounts never submit an activity at all: `markCompleted` is what
 * puts those in the ledger, and it is also what records a hydration, which is not an activity, so
 * `everCompleted` covers both layers on its own.
 *
 * Liveness does not. Hydration has no activity to be active, so `isInitialLoading` reads it
 * from the refresh-state store; without that a chain being read from the DB looks settled-and-empty
 * rather than loading.
 *
 * Aggregate semantics (no chain arg):
 * - hasCachedData: at least one chain has ever completed
 * - isInitialLoading: nothing has ever completed and something is in flight, i.e. there is
 *   genuinely nothing to show yet. Once the first chain lands the rest fill in behind it.
 * - isRefreshing: at least one chain has an in-flight refresh POST. Deliberately *not* hydration:
 *   this is the "user asked for fresh data" spinner, and a DB read is not that.
 */
export function useBalanceStatus(chain?: MaybeRefOrGetter<string>): UseBalanceStatusReturn {
  const { statusOfPrefix, useWorkStatus, version } = useTaskOrchestrator();
  const refreshState = useBalanceRefreshState();

  /** The chain's prefix comes from the descriptor, re-read when the chain or the ledger changes. */
  const chainStatus = (selected: MaybeRefOrGetter<string>): ComputedRef<WorkStatus> => computed<WorkStatus>(() => {
    get(version);
    return statusOfPrefix(chainBalancesActivity.kind, ...chainBalancesActivity.partsWithin([toValue(selected)]));
  });

  const status = chain === undefined
    ? useWorkStatus(chainBalancesActivity.kind)
    : chainStatus(chain);

  const { isHydrating: anyIsHydrating } = storeToRefs(refreshState);
  const hydrating = chain === undefined
    ? anyIsHydrating
    : refreshState.useIsHydrating(chain);

  const hasCachedData = computed<boolean>(() => get(status).everCompleted);

  const isInitialLoading = computed<boolean>(() => {
    const { active, everCompleted } = get(status);
    return (active || get(hydrating)) && !everCompleted;
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

interface ChainLoadStateOptions {
  /**
   * Also count a chain that has never completed as loading until the login load settles, when it
   * may not have started yet and so is neither active nor hydrating.
   */
  readonly untilFirstLoad?: boolean;
}

interface UseChainLoadStatesReturn {
  /** The chains with nothing to show *yet*: busy with their first load. */
  loading: ComputedRef<string[]>;
  /** The chains whose balances are unknown: never loaded, or their last load failed, and idle now. */
  unloaded: ComputedRef<string[]>;
}

/**
 * The per-chain {@link useBalanceStatus} `isInitialLoading`, for a list of chains, plus the chains
 * whose balances are unknown rather than loading.
 *
 * @remarks
 * A chain that completed once is not loading again on a later refresh, so a chain known to be empty
 * does not flicker into a loading state every time balances refresh. A chain the user switched off
 * ends `skipped`, which is neither loading nor unknown.
 */
export function useChainLoadStates(chains: MaybeRefOrGetter<string[]>, options: ChainLoadStateOptions = {}): UseChainLoadStatesReturn {
  const { untilFirstLoad = false } = options;
  const { statusOfPrefix, version } = useTaskOrchestrator();
  const { firstLoadSettled, hydratingChains } = storeToRefs(useBalanceRefreshState());

  /**
   * The chains matching `pick`, read on every ledger change but handed on only when the list itself
   * changed, so a task event elsewhere does not re-render what shows it.
   */
  const chainsWhere = (pick: (status: WorkStatus, busy: boolean, settled: boolean) => boolean): ComputedRef<string[]> =>
    computed<string[]>((previous) => {
      get(version);
      const hydrating = get(hydratingChains);
      const settled = get(firstLoadSettled);
      const next = toValue(chains).filter((chain) => {
        const status = statusOfPrefix(chainBalancesActivity.kind, ...chainBalancesActivity.partsWithin([chain]));
        return pick(status, status.active || hydrating.has(chain), settled);
      });
      return previous && isEqual(previous, next) ? previous : next;
    });

  const loading = chainsWhere(({ everCompleted }, busy, settled) =>
    !everCompleted && (busy || (untilFirstLoad && !settled)));

  const unloaded = chainsWhere(({ everCompleted, lastOutcome }, busy, settled) =>
    !busy
    && (settled || !untilFirstLoad || everCompleted)
    && lastOutcome !== ActivityStatus.SKIPPED
    && (!everCompleted || lastOutcome === ActivityStatus.FAILED));

  return { loading, unloaded };
}
