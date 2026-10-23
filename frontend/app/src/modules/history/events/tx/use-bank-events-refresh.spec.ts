import type { BankConnection, BankConnectionIdentity } from '@/modules/banks/types';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { BackendCancelled, Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useBankEventsRefresh } from './use-bank-events-refresh';

const mockNotifyError = vi.fn();
const mocks = vi.hoisted(() => ({
  getBanks: vi.fn(),
  notify: vi.fn(),
  submitTask: vi.fn(),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn(() => ({ notify: mocks.notify, notifyError: mockNotifyError })),
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
  useBanksApi: vi.fn(() => ({ getBanks: mocks.getBanks, syncBanks: vi.fn() })),
}));

function listed(identity: BankConnectionIdentity, authChallenge: BankConnection['syncStatus']['authChallenge']): BankConnection {
  return { ...identity, displayName: 'FinTS', syncStatus: { authChallenge, authExpired: false, lastError: null, lastSyncTs: null, running: false } };
}

const tanChallenge = { challenge: 'Enter the TAN', challengeData: null, challengeHtml: null, challengeMimeType: null, primitive: 'otp input' as const, prompt: 'Enter the TAN' };

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

  it.each([
    ['succeeded', ok(undefined)],
    ['failed', err(TaskFailed({ message: 'boom' }))],
  ])('should re-read the connections once after the syncs %s', async (_case, outcome) => {
    mocks.submitTask.mockResolvedValue(outcome);
    mocks.getBanks.mockResolvedValue([listed(banks[0], null), listed(banks[1], null)]);

    await useBankEventsRefresh().queryAllBankEvents(banks);

    expect(mocks.getBanks).toHaveBeenCalledOnce();
    expect(useBankConnectionsStore().connections).toEqual([listed(banks[0], null), listed(banks[1], null)]);
  });

  it('should not notify when its activity is cancelled', async () => {
    mocks.submitTask.mockResolvedValue(err(Cancelled({ message: 'cancelled' })));

    const { queryAllBankEvents } = useBankEventsRefresh();
    await queryAllBankEvents([banks[0]]);

    expect(mockNotifyError).not.toHaveBeenCalled();
    expect(mocks.notify).not.toHaveBeenCalled();
  });

  describe('a sync the bank paused for authentication', () => {
    const paused = err(BackendCancelled({ message: 'Backend cancelled task_id: 3, task: bank sync' }));

    it('should store the challenge for the action center without a notification', async () => {
      mocks.submitTask.mockResolvedValue(paused);
      mocks.getBanks.mockResolvedValue([listed(banks[0], tanChallenge), listed(banks[1], null)]);

      const outcomes = await useBankEventsRefresh().queryAllBankEvents([banks[0]]);

      expect(outcomes).toEqual([paused]);
      expect(useBankConnectionsStore().connections).toEqual([listed(banks[0], tanChallenge), listed(banks[1], null)]);
      expect(mocks.notify).not.toHaveBeenCalled();
      expect(mockNotifyError).not.toHaveBeenCalled();
    });

    it('should keep the stored connections when they cannot be listed', async () => {
      useBankConnectionsStore().setConnections([listed(banks[0], null)]);
      mocks.submitTask.mockResolvedValue(paused);
      mocks.getBanks.mockRejectedValue(new Error('offline'));

      const outcomes = await useBankEventsRefresh().queryAllBankEvents([banks[0]]);

      expect(outcomes).toEqual([paused]);
      expect(useBankConnectionsStore().connections).toEqual([listed(banks[0], null)]);
    });
  });

  it('should hand an actionable failure back and leave it to its dock row', async () => {
    mocks.submitTask.mockResolvedValue(err(TaskFailed({ message: 'boom' })));

    const { queryAllBankEvents } = useBankEventsRefresh();
    const outcomes = await queryAllBankEvents([banks[0]]);

    expect(outcomes).toHaveLength(1);
    expect(mockNotifyError).not.toHaveBeenCalled();
  });
});
