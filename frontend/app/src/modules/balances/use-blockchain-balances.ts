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

interface UseBlockchainBalancesReturn {
  refreshBlockchainBalances: (payload?: BlockchainBalancePayload, periodic?: boolean) => Promise<void>;
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
  const { submitTask } = useNativeTask();
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
   * ⚠️ The remaining half is not redundant with `submitTask`'s id dedup, and must not be deleted
   * with it. Dedup *joins* a caller to the run already in flight; this makes a manual refresh wait
   * and then genuinely re-query, which is what a user asking for fresh data expects. Deleting it
   * would silently hand them the periodic run's result instead — the supersede gap, which has no
   * implementation yet.
   */
  const isChainRefreshing = (chain: string): boolean => get(refreshState.refreshingChains).has(chain);

  // Network refresh — one native BLOCKCHAIN_BALANCES activity per chain on BALANCES_LANE (cap 2,
  // paused during decode by the orchestrator rule, replacing the old BalanceQueueService).
  const refreshBlockchainBalances = async (
    payload: BlockchainBalancePayload = {},
    periodic = false,
  ): Promise<void> => {
    const { addresses, blockchain, isXpub = false } = payload;
    const chains = blockchain ? arrayify(blockchain) : get(supportedChains).map(chain => chain.id);
    await Promise.allSettled(
      chains.map(async (chain) => {
        const chainPayload = { addresses, blockchain: chain, isXpub };
        if (!shouldQuery(chain)) {
          clearChainBalances(chain);
          return;
        }
        await submitTask({
          id: makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, chain),
          kind: ActivityKind.BLOCKCHAIN_BALANCES,
          lane: BALANCES_LANE,
          rerunnable: true,
          run: async ({ runTask }): Promise<Result<void, TaskError>> => {
            if (isChainRefreshing(chain)) {
              // 🔴 A dropped refresh is SKIPPED with a reason, never `ok`. Returning success here
              // recorded a completion for work that never ran, so the ledger — and `everCompleted`
              // with it — reported this chain as refreshed. Same class as a green "Sync Complete"
              // over chains that were never synced.
              //
              // `Skipped` is not `isActionable`, so this raises no notification; it settles the
              // activity terminal-but-not-successful and the task centre renders the reason.
              if (periodic)
                return err(Skipped({ message: t('actions.balances.blockchain.skipped.busy') }));

              await until(() => isChainRefreshing(chain)).toBe(false);
            }
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
