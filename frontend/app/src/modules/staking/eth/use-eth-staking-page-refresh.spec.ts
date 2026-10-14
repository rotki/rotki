import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref } from 'vue';
import { OnlineHistoryEventsQueryType } from '@/modules/history/events/schemas';
import { useEthStakingPageRefresh } from '@/modules/staking/eth/use-eth-staking-page-refresh';
import { ActivityKind } from '@/modules/task-center/core/types';

const reloadEvents = vi.fn();
const queryOnlineEvent = vi.fn(async (): Promise<void> => {});
const withdrawalsLoading = ref<boolean>(false);
const useIsActive = vi.fn(() => computed<boolean>(() => get(withdrawalsLoading)));

vi.mock('@/modules/history/events/use-history-events-section', () => ({
  provideHistoryEventsSection: vi.fn(() => ({ reload: reloadEvents })),
}));

vi.mock('@/modules/history/events/tx/use-refresh-handlers', () => ({
  useRefreshHandlers: vi.fn(() => ({ queryOnlineEvent })),
}));

vi.mock('@/modules/staking/use-staking-history-sync', () => ({
  useStakingHistorySync: vi.fn(() => ({
    chainName: computed<string>(() => 'Ethereum'),
    syncHistory: vi.fn(),
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

  it('should count as refreshing while the staking figures or the withdrawals load', () => {
    const { refreshing } = useEthStakingPageRefresh(refreshStaking, computed<boolean>(() => get(stakingRefreshing)));

    expect(useIsActive).toHaveBeenCalledWith(ActivityKind.ONLINE_EVENTS, OnlineHistoryEventsQueryType.ETH_WITHDRAWALS);
    expect(get(refreshing)).toBe(false);

    set(stakingRefreshing, true);
    expect(get(refreshing)).toBe(true);

    set(stakingRefreshing, false);
    set(withdrawalsLoading, true);
    expect(get(refreshing)).toBe(true);
  });

  it('should pass the history sync through for the refresh menu', () => {
    const { chainName, syncingHistory } = useEthStakingPageRefresh(refreshStaking, computed<boolean>(() => get(stakingRefreshing)));

    expect(get(chainName)).toBe('Ethereum');
    expect(get(syncingHistory)).toBe(false);
  });
});
