import type { ComputedRef } from 'vue';
import { OnlineHistoryEventsQueryType } from '@/modules/history/events/schemas';
import { useRefreshHandlers } from '@/modules/history/events/tx/use-refresh-handlers';
import { provideHistoryEventsSection } from '@/modules/history/events/use-history-events-section';
import { useStakingHistorySync } from '@/modules/staking/use-staking-history-sync';
import { ActivityKind, useTaskCenter } from '@/modules/task-center/use-task-center';

interface UseEthStakingPageRefreshReturn {
  chainName: ComputedRef<string>;
  /** Staking events being queried that neither the page's Refresh nor its history sync asked for. */
  queryingEvents: ComputedRef<boolean>;
  refreshPage: () => Promise<void>;
  /** The page's figures loading, or its own Refresh running until every query it started settles. */
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
  const { chainName, syncHistory: syncChainHistory, syncingHistory } = useStakingHistorySync(reloadEvents);
  const { useIsActive } = useTaskCenter();

  const pageRefreshing = shallowRef<boolean>(false);
  /**
   * Only the sync this page's menu started. `syncingHistory` cannot stand in for it: the events
   * section's own refresh runs under the same history sync activity.
   */
  const pageSyncing = shallowRef<boolean>(false);

  const eventsLoading = logicOr(
    useIsActive(ActivityKind.ONLINE_EVENTS, OnlineHistoryEventsQueryType.ETH_WITHDRAWALS),
    useIsActive(ActivityKind.ONLINE_EVENTS, OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS),
  );

  const refreshing = logicOr(stakingRefreshing, pageRefreshing);
  const queryingEvents = logicAnd(eventsLoading, logicNot(logicOr(pageRefreshing, pageSyncing)));

  async function refreshPage(): Promise<void> {
    set(pageRefreshing, true);
    try {
      await Promise.all([
        refreshStaking(true),
        queryOnlineEvent(OnlineHistoryEventsQueryType.ETH_WITHDRAWALS),
        queryOnlineEvent(OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS),
      ]);
    }
    finally {
      set(pageRefreshing, false);
    }
    reloadEvents();
  }

  async function syncHistory(): Promise<void> {
    set(pageSyncing, true);
    try {
      await syncChainHistory();
    }
    finally {
      set(pageSyncing, false);
    }
  }

  return {
    chainName,
    queryingEvents,
    refreshPage,
    refreshing,
    syncHistory,
    syncingHistory,
  };
}
