import type { BlockchainBalancePayload } from '@/modules/balances/types/blockchain-balances';
import { err, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { arrayify } from '@/modules/core/common/data/array';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { Skipped, type TaskError } from '@/modules/core/tasks/task-result';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { BALANCES_LANE } from '@/modules/task-center/core/orchestrator/spec';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';
import { useBalanceProcessingService } from './services/use-balance-processing-service';

/**
 * Who asked for this refresh, which is what decides what happens when the chain is already busy.
 *
 * - `background`: join the run in flight. Two callers wanting the same thing share one query.
 * - `periodic`: settle SKIPPED with a reason. A tick that finds the chain busy has nothing to add,
 *   and recording it as `ok` would mark the chain refreshed when nothing ran.
 * - `user`: supersede. Someone pressed refresh, so they get a fresh query with *their* parameters
 *   rather than whatever the background run happened to be doing.
 */
export type RefreshMode = 'background' | 'periodic' | 'user';

interface UseBlockchainBalancesReturn {
  refreshBlockchainBalances: (payload?: BlockchainBalancePayload, mode?: RefreshMode) => Promise<void>;
}

/**
 * Layer 2 — the work.
 *
 * The network query a user watches, cancels and retries: one activity per chain, on a lane, in the
 * task centre. Reading a chain's balances back out of the user's own database is the *other*
 * layer and lives in {@link useBalanceHydration} — it is not work, so it is not here.
 */
export function useBlockchainBalances(): UseBlockchainBalancesReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { getChainName, supportedChains } = useSupportedChains();

  const { clearChainBalances, handleRefresh, shouldQuery } = useBalanceProcessingService();
  const { submitTask, supersedeTask } = useNativeTask();
  const refreshState = useBalanceRefreshState();

  /**
   * Whether a *network* refresh is already running for this chain.
   *
   * ⭐ It does not wait on the chain's hydration from the DB, and must not: the two layers overlap
   * by design. A cached read landing after a network result would overwrite fresh balances with
   * stale ones, which balance writes being monotonic prevents outright — the older payload is
   * discarded whichever order the two land in. Two mechanisms for one hazard, and the cheaper one
   * wins.
   *
   * ⚠️ Read by the `periodic` branch only. It is not redundant with `submitTask`'s id dedup: dedup
   * covers a run that is *submitted*, this covers the window where the POST itself is in flight.
   */
  const isChainRefreshing = (chain: string): boolean => get(refreshState.refreshingChains).has(chain);

  // Network refresh — one native BLOCKCHAIN_BALANCES activity per chain on BALANCES_LANE (cap 2,
  // paused during decode by the orchestrator rule, replacing the old BalanceQueueService).
  const refreshBlockchainBalances = async (
    payload: BlockchainBalancePayload = {},
    mode: RefreshMode = 'background',
  ): Promise<void> => {
    const { addresses, blockchain, isXpub = false } = payload;
    const chains = blockchain ? arrayify(blockchain) : get(supportedChains).map(chain => chain.id);
    // ⭐ A user-initiated refresh replaces the run in flight instead of joining it. `supersedeTask`
    // is the single shared helper for that — cancel, *await the cancelled promise*, then submit —
    // because `finish()` is what frees the id, and resubmitting before it dedups onto the corpse.
    //
    // This is what retired the old `until(() => isChainRefreshing(chain)).toBe(false)` poll on the
    // non-periodic path. That poll was standing in for supersede: it made a manual refresh wait for
    // the background run to finish and then re-query, which is the right *outcome* reached by
    // waiting out work the user had already superseded.
    const submit = mode === 'user' ? supersedeTask : submitTask;
    await Promise.allSettled(
      chains.map(async (chain) => {
        const chainPayload = { addresses, blockchain: chain, isXpub };
        if (!shouldQuery(chain)) {
          clearChainBalances(chain);
          return;
        }
        await submit({
          id: makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, chain),
          kind: ActivityKind.BLOCKCHAIN_BALANCES,
          lane: BALANCES_LANE,
          rerunnable: true,
          run: async ({ runTask }): Promise<Result<void, TaskError>> => {
            // 🔴 A dropped refresh is SKIPPED with a reason, never `ok`. Returning success here
            // recorded a completion for work that never ran, so the ledger — and `everCompleted`
            // with it — reported this chain as refreshed. Same class as a green "Sync Complete"
            // over chains that were never synced.
            //
            // `Skipped` is not `isActionable`, so this raises no notification; it settles the
            // activity terminal-but-not-successful and the task centre renders the reason.
            if (mode === 'periodic' && isChainRefreshing(chain))
              return err(Skipped({ message: t('actions.balances.blockchain.skipped.busy') }));

            return handleRefresh(runTask, chainPayload);
          },
          subtitle: activityLabelFor(msg.$t('task_center.activity.blockchain_balances.query'), { chain: getChainName(chain) }),
          title: t('task_center.group.blockchain_balances'),
        });
      }),
    );
  };

  return {
    refreshBlockchainBalances,
  };
}
