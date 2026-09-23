import type { Notification } from '@rotki/common';
import type { BankConnection, BankConnectionIdentity, BankManifest } from '@/modules/banks/types';
import { createMock } from '@test/utils/create-mock';
import { createLocationNode } from '@test/utils/location-tree';
import { err, ok } from 'plainfp/result';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { BackendCancelled, Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useBankEventsRefresh } from './use-bank-events-refresh';

const mockNotifyError = vi.fn();
const mocks = vi.hoisted(() => ({
  getBanks: vi.fn(),
  notify: vi.fn(),
  push: vi.fn(),
  submitTask: vi.fn(),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn(() => ({ notify: mocks.notify, notifyError: mockNotifyError })),
}));

vi.mock('@/router', () => ({
  router: { push: mocks.push },
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
  return { ...identity, connector: 'qonto', displayName: 'FinTS', syncStatus: { authChallenge, lastError: null, lastSyncTs: null, running: false } };
}

const tanChallenge = { challenge: 'Enter the TAN', challengeData: null, challengeHtml: null, challengeMimeType: null, primitive: 'otp input' as const, prompt: 'Enter the TAN' };

describe('useBankEventsRefresh', () => {
  const banks: BankConnectionIdentity[] = [
    { identifier: 'c1', location: 'qonto', name: 'Qonto main' },
    { identifier: 'c2', location: 'qonto', name: 'Qonto side' },
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

  it('should not notify when its activity is cancelled', async () => {
    mocks.submitTask.mockResolvedValue(err(Cancelled({ message: 'cancelled' })));

    const { queryAllBankEvents } = useBankEventsRefresh();
    await queryAllBankEvents([banks[0]]);

    expect(mockNotifyError).not.toHaveBeenCalled();
    expect(mocks.notify).not.toHaveBeenCalled();
  });

  describe('a sync the bank paused for authentication', () => {
    const paused = err(BackendCancelled({ message: 'Backend cancelled task_id: 3, task: bank sync' }));

    it('should ask the user to authenticate', async () => {
      mocks.submitTask.mockResolvedValue(paused);
      mocks.getBanks.mockResolvedValue([listed(banks[0], tanChallenge), listed(banks[1], null)]);

      const outcomes = await useBankEventsRefresh().queryAllBankEvents([banks[0]]);

      expect(outcomes).toEqual([paused]);
      expect(mockNotifyError).not.toHaveBeenCalled();
      expect(mocks.notify).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({
        message: 'actions.bank_events.authentication.description::Qonto, Qonto main',
        title: 'actions.bank_events.authentication.title',
      }));
      expect(useBankConnectionsStore().connections).toEqual([listed(banks[0], tanChallenge), listed(banks[1], null)]);
    });

    it('should open the authentication of that connection from the notification', async () => {
      mocks.submitTask.mockResolvedValue(paused);
      mocks.getBanks.mockResolvedValue([listed(banks[0], tanChallenge)]);

      await useBankEventsRefresh().queryAllBankEvents([banks[0]]);
      const notification: Notification = mocks.notify.mock.calls[0][0];
      assert(notification.action && !Array.isArray(notification.action));
      await notification.action.action();

      expect(mocks.push).toHaveBeenCalledExactlyOnceWith({ name: '/api-keys/banks/', query: { authenticate: 'c1' } });
    });

    it.each([
      ['has no pending challenge', async (): Promise<void> => { mocks.getBanks.mockResolvedValue([listed(banks[0], null)]); }],
      ['cannot be listed', async (): Promise<void> => { mocks.getBanks.mockRejectedValue(new Error('offline')); }],
    ])('should not ask for authentication when the connection %s', async (_case, arrange) => {
      mocks.submitTask.mockResolvedValue(paused);
      await arrange();

      await useBankEventsRefresh().queryAllBankEvents([banks[0]]);

      expect(mocks.notify).not.toHaveBeenCalled();
    });

    it('should not look for a challenge when the user cancelled the sync', async () => {
      mocks.submitTask.mockResolvedValue(err(Cancelled({ message: 'cancelled' })));

      await useBankEventsRefresh().queryAllBankEvents([banks[0]]);

      expect(mocks.getBanks).not.toHaveBeenCalled();
    });
  });

  it('should notify on an actionable failure and hand the outcome back', async () => {
    mocks.submitTask.mockResolvedValue(err(TaskFailed({ message: 'boom' })));

    const { queryAllBankEvents } = useBankEventsRefresh();
    const outcomes = await queryAllBankEvents([banks[0]]);

    expect(outcomes).toHaveLength(1);
    expect(mockNotifyError).toHaveBeenCalledOnce();
    expect(mockNotifyError.mock.calls[0][1]).toContain('boom');
  });

  it('should name the bank by its connector display name in the failure notification', async () => {
    useBankConnectionsStore().setManifests([createMock<BankManifest>({ connectorIdentifier: 'qonto', displayName: 'Qonto Business' })]);
    useBankConnectionsStore().setConnections([listed(banks[0], null)]);
    mocks.submitTask.mockResolvedValue(err(TaskFailed({ message: 'boom' })));

    const { queryAllBankEvents } = useBankEventsRefresh();
    await queryAllBankEvents([banks[0]]);

    expect(mockNotifyError.mock.calls[0][1]).toContain('Qonto Business');
  });

  it('should name a FinTS connection by the bank its data belongs to, not by the connector', async () => {
    const giro: BankConnectionIdentity = { identifier: 'c3', location: 'custom:ing', name: 'Giro' };
    useLocationTreeStore().setNodes([createLocationNode('custom:ing', 'banks', 'ING', { isBuiltin: false })]);
    useBankConnectionsStore().setManifests([createMock<BankManifest>({ connectorIdentifier: 'fints', displayName: 'FinTS/HBCI' })]);
    useBankConnectionsStore().setConnections([{ ...listed(giro, null), connector: 'fints' }]);
    mocks.submitTask.mockResolvedValue(err(TaskFailed({ message: 'boom' })));

    await useBankEventsRefresh().queryAllBankEvents([giro]);

    expect(mockNotifyError.mock.calls[0][1]).toBe('actions.bank_events.error.description::boom, ING, Giro');
  });
});
