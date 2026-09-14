import type { BankConnectionIdentity } from '@/modules/banks/types';
import type { useBanksApi } from '@/modules/banks/use-banks-api';
import { createMock } from '@test/utils/create-mock';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useBankEventsRefresh } from './use-bank-events-refresh';

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

vi.mock('@/modules/banks/use-banks-api', () => ({
  useBanksApi: vi.fn(() => createMock<ReturnType<typeof useBanksApi>>()),
}));

vi.mock('@/modules/history/use-events-query-status-store', () => ({
  useEventsQueryStatusStore: vi.fn(() => ({ markLocationCancelled: mocks.markLocationCancelled })),
}));

describe('useBankEventsRefresh', () => {
  const banks: BankConnectionIdentity[] = [
    { location: 'qonto', name: 'Qonto main' },
    { location: 'qonto', name: 'Qonto side' },
  ];

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mocks.submitTask.mockResolvedValue(ok(undefined));
  });

  it('should submit one native activity per bank connection on the bank lane', async () => {
    const { queryAllBankEvents } = useBankEventsRefresh();
    await queryAllBankEvents(banks);

    expect(mocks.submitTask).toHaveBeenCalledTimes(2);
    const ids = mocks.submitTask.mock.calls.map(([spec]) => spec.id).sort();
    expect(ids).toStrictEqual([
      makeActivityId(ActivityKind.BANK_EVENTS, 'qonto', 'Qonto main'),
      makeActivityId(ActivityKind.BANK_EVENTS, 'qonto', 'Qonto side'),
    ].sort());
    expect(mocks.submitTask.mock.calls[0][0]).toMatchObject({
      kind: ActivityKind.BANK_EVENTS,
      lane: 'bank-events:qonto',
      rerunnable: true,
    });
  });

  it('should mark the connection cancelled when its activity is cancelled', async () => {
    mocks.submitTask.mockResolvedValue(err(Cancelled({ message: 'cancelled' })));

    const { queryAllBankEvents } = useBankEventsRefresh();
    await queryAllBankEvents([banks[0]]);

    expect(mocks.markLocationCancelled).toHaveBeenCalledWith({ location: 'qonto', name: 'Qonto main' });
    expect(mockNotifyError).not.toHaveBeenCalled();
  });

  it('should notify on an actionable failure and hand the outcome back', async () => {
    mocks.submitTask.mockResolvedValue(err(TaskFailed({ message: 'boom' })));

    const { queryAllBankEvents } = useBankEventsRefresh();
    const outcomes = await queryAllBankEvents([banks[0]]);

    expect(outcomes).toHaveLength(1);
    expect(mockNotifyError).toHaveBeenCalledOnce();
    expect(mockNotifyError.mock.calls[0][1]).toContain('boom');
  });
});
