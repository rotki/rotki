import type { ComputedRef } from 'vue';
import { OnlineHistoryEventsQueryType } from '@/modules/history/events/schemas';
import { useRefreshHandlers } from '@/modules/history/events/tx/use-refresh-handlers';
import { provideHistoryEventsSection } from '@/modules/history/events/use-history-events-section';
import { useStakingHistorySync } from '@/modules/staking/use-staking-history-sync';
import { ActivityKind, useTaskCenter } from '@/modules/task-center/use-task-center';

interface UseEthStakingPageRefreshReturn {
  chainName: ComputedRef<string>;
  refreshPage: () => Promise<void>;
  refreshing: ComputedRef<boolean>;
  syncHistory: () => Promise<void>;
  syncingHistory: ComputedRef<boolean>;
}

/**
 * The ETH staking page's one refresh: the staking figures, plus the staking events below them.
 *
 * @remarks
 * The events used to carry their own refresh, which ran the full history sync: every account,
 * exchange and bank. Here only the two sources staking events come from are queried, withdrawals
 * and block production, and the events section then reads its events again. Deposits are decoded
 * from transactions, so they arrive with the history sync, which stays available as `syncHistory`
 * for the refresh menu.
 *
 * Provides the events section context, so it must be called from the page's setup.
 */
export function useEthStakingPageRefresh(
  refreshStaking: (userInitiated: boolean) => Promise<void>,
  stakingRefreshing: ComputedRef<boolean>,
): UseEthStakingPageRefreshReturn {
  const { reload: reloadEvents } = provideHistoryEventsSection();
  const { queryOnlineEvent } = useRefreshHandlers();
  const { chainName, syncHistory, syncingHistory } = useStakingHistorySync(reloadEvents);
  const { useIsActive } = useTaskCenter();

  const withdrawalsLoading = useIsActive(ActivityKind.ONLINE_EVENTS, OnlineHistoryEventsQueryType.ETH_WITHDRAWALS);

  const refreshing = logicOr(stakingRefreshing, withdrawalsLoading);

  async function refreshPage(): Promise<void> {
    await Promise.all([
      refreshStaking(true),
      queryOnlineEvent(OnlineHistoryEventsQueryType.ETH_WITHDRAWALS),
      queryOnlineEvent(OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS),
    ]);
    reloadEvents();
  }

  return {
    chainName,
    refreshPage,
    refreshing,
    syncHistory,
    syncingHistory,
  };
}
