import type { Exchange } from '@/modules/balances/types/exchanges';
import type { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { createMock } from '@test/utils/create-mock';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useExchangeEventsRefresh } from './use-exchange-events-refresh';

const mockNotifyError = vi.fn();
const mocks = vi.hoisted(() => ({
  markLocationCancelled: vi.fn(),
  submitTask: vi.fn(),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn(() => ({ notifyError: mockNotifyError })),
}));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: vi.fn(() => ({
    cancelByType: vi.fn(() => vi.fn()),
    reportProgress: vi.fn(),
    runTaskResult: vi.fn(),
    submitTask: mocks.submitTask,
  })),
}));

vi.mock('@/modules/history/api/events/use-history-events-api', () => ({
  useHistoryEventsApi: vi.fn(() => createMock<ReturnType<typeof useHistoryEventsApi>>()),
}));

vi.mock('@/modules/history/use-events-query-status-store', () => ({
  useEventsQueryStatusStore: vi.fn(() => ({ markLocationCancelled: mocks.markLocationCancelled })),
}));

describe('useExchangeEventsRefresh', () => {
  const exchanges: Exchange[] = [
    { location: 'kraken', name: 'kraken 1' },
    { location: 'binance', name: 'binance 1' },
  ];

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mocks.submitTask.mockResolvedValue(ok(undefined));
  });

  it('should submit one native activity per exchange account', async () => {
    const { queryAllExchangeEvents } = useExchangeEventsRefresh();
    await queryAllExchangeEvents(exchanges);

    expect(mocks.submitTask).toHaveBeenCalledTimes(2);
    const ids = mocks.submitTask.mock.calls.map(([spec]) => spec.id).sort();
    expect(ids).toStrictEqual([
      makeActivityId(ActivityKind.EXCHANGE_EVENTS, 'binance', 'binance 1'),
      makeActivityId(ActivityKind.EXCHANGE_EVENTS, 'kraken', 'kraken 1'),
    ].sort());
    expect(mocks.submitTask.mock.calls[0][0]).toMatchObject({
      kind: ActivityKind.EXCHANGE_EVENTS,
      rerunnable: true,
    });
  });

  it('should mark the location cancelled when an activity is cancelled', async () => {
    mocks.submitTask.mockResolvedValue(err(Cancelled({ message: 'cancelled' })));

    const { queryAllExchangeEvents } = useExchangeEventsRefresh();
    await queryAllExchangeEvents([{ location: 'kraken', name: 'kraken 1' }]);

    expect(mocks.markLocationCancelled).toHaveBeenCalledWith({ location: 'kraken', name: 'kraken 1' });
    expect(mockNotifyError).not.toHaveBeenCalled();
  });

  it('should notify on an actionable failure', async () => {
    mocks.submitTask.mockResolvedValue(err(TaskFailed({ message: 'boom' })));

    const { queryAllExchangeEvents } = useExchangeEventsRefresh();
    await queryAllExchangeEvents([{ location: 'kraken', name: 'kraken 1' }]);

    expect(mockNotifyError).toHaveBeenCalledOnce();
    expect(mocks.markLocationCancelled).not.toHaveBeenCalled();
  });

  it('should stay quiet on success', async () => {
    const { queryAllExchangeEvents } = useExchangeEventsRefresh();
    await queryAllExchangeEvents([{ location: 'kraken', name: 'kraken 1' }]);

    expect(mockNotifyError).not.toHaveBeenCalled();
    expect(mocks.markLocationCancelled).not.toHaveBeenCalled();
  });
});
