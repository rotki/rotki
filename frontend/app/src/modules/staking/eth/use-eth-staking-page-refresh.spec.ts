import type { useTaskCenter } from '@/modules/task-center/use-task-center';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref } from 'vue';
import { OnlineHistoryEventsQueryType } from '@/modules/history/events/schemas';
import { useEthStakingPageRefresh } from '@/modules/staking/eth/use-eth-staking-page-refresh';
import { ActivityKind } from '@/modules/task-center/core/types';

const reloadEvents = vi.fn();
const queryOnlineEvent = vi.fn(async (): Promise<void> => {});
const syncChainHistory = vi.fn(async (): Promise<void> => {});
const withdrawalsLoading = ref<boolean>(false);
const blockProductionsLoading = ref<boolean>(false);
const useIsActive = vi.fn<ReturnType<typeof useTaskCenter>['useIsActive']>((_kind, queryType) => computed<boolean>(() =>
  get(queryType === OnlineHistoryEventsQueryType.ETH_WITHDRAWALS ? withdrawalsLoading : blockProductionsLoading)));

vi.mock('@/modules/history/events/use-history-events-section', () => ({
  provideHistoryEventsSection: vi.fn(() => ({ reload: reloadEvents })),
}));

vi.mock('@/modules/history/events/tx/use-refresh-handlers', () => ({
  useRefreshHandlers: vi.fn(() => ({ queryOnlineEvent })),
}));

vi.mock('@/modules/staking/use-staking-history-sync', () => ({
  useStakingHistorySync: vi.fn(() => ({
    chainName: computed<string>(() => 'Ethereum'),
    syncHistory: syncChainHistory,
    syncingHistory: computed<boolean>(() => false),
  })),
}));

vi.mock('@/modules/task-center/use-task-center', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useTaskCenter: vi.fn(() => ({ useIsActive })),
}));

describe('useEthStakingPageRefresh', () => {
  const stakingRefreshing = ref<boolean>(false);
  const refreshStaking = vi.fn(async (): Promise<void> => {});

  beforeEach(() => {
    vi.clearAllMocks();
    set(stakingRefreshing, false);
    set(withdrawalsLoading, false);
    set(blockProductionsLoading, false);
  });

  it('should query the staking figures and only the two staking event sources, then reload the events', async () => {
    const { refreshPage } = useEthStakingPageRefresh(refreshStaking, computed<boolean>(() => get(stakingRefreshing)));

    await refreshPage();

    expect(refreshStaking).toHaveBeenCalledWith(true);
    expect(queryOnlineEvent).toHaveBeenCalledTimes(2);
    expect(queryOnlineEvent).toHaveBeenCalledWith(OnlineHistoryEventsQueryType.ETH_WITHDRAWALS);
    expect(queryOnlineEvent).toHaveBeenCalledWith(OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS);
    expect(reloadEvents).toHaveBeenCalledOnce();
  });

  it('should reload the events only after every query settles', async () => {
    let finishWithdrawals: () => void = () => {};
    queryOnlineEvent.mockImplementationOnce(async () => new Promise<void>((resolve) => {
      finishWithdrawals = resolve;
    }));
    const { refreshPage } = useEthStakingPageRefresh(refreshStaking, computed<boolean>(() => get(stakingRefreshing)));

    const pending = refreshPage();
    await Promise.resolve();
    expect(reloadEvents).not.toHaveBeenCalled();

    finishWithdrawals();
    await pending;
    expect(reloadEvents).toHaveBeenCalledOnce();
  });

  it('should count as refreshing while the staking figures load', () => {
    const { refreshing } = useEthStakingPageRefresh(refreshStaking, computed<boolean>(() => get(stakingRefreshing)));

    expect(get(refreshing)).toBe(false);

    set(stakingRefreshing, true);
    expect(get(refreshing)).toBe(true);
  });

  it('should not count staking events queried without its refresh as refreshing, but report them as querying', () => {
    const { queryingEvents, refreshing } = useEthStakingPageRefresh(refreshStaking, computed<boolean>(() => get(stakingRefreshing)));

    expect(useIsActive).toHaveBeenCalledWith(ActivityKind.ONLINE_EVENTS, OnlineHistoryEventsQueryType.ETH_WITHDRAWALS);
    expect(useIsActive).toHaveBeenCalledWith(ActivityKind.ONLINE_EVENTS, OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS);
    expect(get(queryingEvents)).toBe(false);

    set(blockProductionsLoading, true);
    expect(get(refreshing)).toBe(false);
    expect(get(queryingEvents)).toBe(true);

    set(blockProductionsLoading, false);
    set(withdrawalsLoading, true);
    expect(get(refreshing)).toBe(false);
    expect(get(queryingEvents)).toBe(true);
  });

  it('should count as refreshing until its own refresh settles, without also reporting its queries as querying', async () => {
    let finishQuery: () => void = () => {};
    queryOnlineEvent.mockImplementationOnce(async () => new Promise<void>((resolve) => {
      finishQuery = resolve;
    }));
    const { queryingEvents, refreshPage, refreshing } = useEthStakingPageRefresh(refreshStaking, computed<boolean>(() => get(stakingRefreshing)));

    const pending = refreshPage();
    set(blockProductionsLoading, true);
    expect(get(refreshing)).toBe(true);
    expect(get(queryingEvents)).toBe(false);

    finishQuery();
    set(blockProductionsLoading, false);
    await pending;
    expect(get(refreshing)).toBe(false);
  });

  it('should not report the staking events its own history sync queries as querying', async () => {
    let finishSync: () => void = () => {};
    syncChainHistory.mockImplementationOnce(async () => new Promise<void>((resolve) => {
      finishSync = resolve;
    }));
    const { queryingEvents, refreshing, syncHistory } = useEthStakingPageRefresh(refreshStaking, computed<boolean>(() => get(stakingRefreshing)));

    const pending = syncHistory();
    set(withdrawalsLoading, true);
    expect(get(queryingEvents)).toBe(false);
    expect(get(refreshing)).toBe(false);

    finishSync();
    await pending;
    expect(syncChainHistory).toHaveBeenCalledOnce();
    expect(get(queryingEvents)).toBe(true);
  });

  it('should pass the history sync through for the refresh menu', () => {
    const { chainName, syncingHistory } = useEthStakingPageRefresh(refreshStaking, computed<boolean>(() => get(stakingRefreshing)));

    expect(get(chainName)).toBe('Ethereum');
    expect(get(syncingHistory)).toBe(false);
  });
});
