import type { BlockchainBalancePayload } from '@/modules/balances/types/blockchain-balances';
import { err, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { useValueThreshold } from '@/modules/assets/amount-display/use-usd-value-threshold';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { arrayify } from '@/modules/core/common/data/array';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { Skipped, type TaskError } from '@/modules/core/tasks/task-result';
import { BalanceSource } from '@/modules/settings/types/frontend-settings';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { BALANCES_LANE } from '@/modules/task-center/core/orchestrator/spec';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';
import { useBalanceProcessingService } from './services/use-balance-processing-service';

interface UseBlockchainBalancesReturn {
  fetchBlockchainBalances: (payload?: BlockchainBalancePayload) => Promise<void>;
  refreshBlockchainBalances: (payload?: BlockchainBalancePayload, periodic?: boolean) => Promise<void>;
}

export function useBlockchainBalances(): UseBlockchainBalancesReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { getChainName, supportedChains } = useSupportedChains();
  const { statusOf, version } = useTaskOrchestrator();
  const valueThreshold = useValueThreshold(BalanceSource.BLOCKCHAIN);

  const { clearChainBalances, handleCachedFetch, handleRefresh, shouldQuery } = useBalanceProcessingService();
  const { submitTask } = useNativeTask();
  const refreshState = useBalanceRefreshState();

  // Deliberately the *cached* activity and not the whole chain prefix: this runs inside the
  // refresh activity itself, so a prefix read would see its own RUNNING status and wait forever.
  // `version` is touched so the `until` below re-evaluates when the cached read settles.
  const isChainBusy = (chain: string): boolean => {
    get(version);
    return statusOf(ActivityKind.BLOCKCHAIN_BALANCES, chain, ActivityPart.CACHED).active
      || get(refreshState.refreshingChains).has(chain);
  };

  // Cached DB read — fires immediately. Each chain with accounts runs as a native
  // BLOCKCHAIN_BALANCES activity on the default (uncapped) lane so initial load is not throttled;
  // empty chains are cleared inline without spawning an activity.
  const fetchBlockchainBalances = async (
    payload: BlockchainBalancePayload = {},
  ): Promise<void> => {
    const { addresses, blockchain, isXpub = false } = payload;
    const chains = blockchain ? arrayify(blockchain) : get(supportedChains).map(chain => chain.id);
    const threshold = get(valueThreshold);
    await Promise.allSettled(
      chains.map(async (chain) => {
        const chainPayload = { addresses, blockchain: chain, isXpub };
        if (!shouldQuery(chain)) {
          clearChainBalances(chain);
          return;
        }
        await submitTask({
          id: makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, chain, ActivityPart.CACHED),
          kind: ActivityKind.BLOCKCHAIN_BALANCES,
          rerunnable: true,
          run: async ({ runTask }): Promise<Result<void, TaskError>> => handleCachedFetch(runTask, chainPayload, threshold),
          subtitle: activityLabelFor(msg.$t('task_center.activity.blockchain_balances.cached'), { chain: getChainName(chain) }),
          title: t('task_center.group.blockchain_balances'),
        });
      }),
    );
  };

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
            if (isChainBusy(chain)) {
              // 🔴 A dropped refresh is SKIPPED with a reason, never `ok`. Returning success here
              // recorded a completion for work that never ran, so the ledger — and `everCompleted`
              // with it — reported this chain as refreshed. Same class as a green "Sync Complete"
              // over chains that were never synced.
              //
              // `Skipped` is not `isActionable`, so this raises no notification; it settles the
              // activity terminal-but-not-successful and the task centre renders the reason.
              if (periodic)
                return err(Skipped({ message: t('actions.balances.blockchain.skipped.busy') }));

              await until(() => isChainBusy(chain)).toBe(false);
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
    fetchBlockchainBalances,
    refreshBlockchainBalances,
  };
}
